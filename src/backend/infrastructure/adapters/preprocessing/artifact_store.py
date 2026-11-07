"""Content-addressed JSON/tokenizer storage; no pickle or uploaded code."""
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
import os
from zipfile import ZipFile, ZIP_DEFLATED
from domain.entities.preprocessing.artifacts import canonical, ExportedArtifact, provenance

class ArtifactUnavailable(RuntimeError):
    pass




class JSONArtifactStore:
    entity = None
    task = None

    def __init__(self, root: Path):
        self.base_root = Path(root)
        self.root = self.base_root / self.task

    def path(self, artifact_id):
        if not isinstance(artifact_id, str) or not re.fullmatch("[0-9a-f]{64}", artifact_id):
            raise ValueError("Invalid artifact ID")
        destination = self.root / artifact_id
        legacy = self.base_root / artifact_id
        if not destination.exists() and (legacy / 'manifest.json').is_file():
            if json.loads((legacy / 'manifest.json').read_text()).get('task') == self.task:
                return legacy
        return destination

    def save(self, prepared, settings, files=None):
        files = files or {}
        manifest = {"schema_version": 1, "task": self.task, "settings": settings,
                    "provenance": provenance(prepared),
                    "files": {name: sha256(content).hexdigest() for name, content in files.items()}}
        artifact = self.entity(canonical(manifest))
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.path(artifact.artifact_id)
        if destination.exists():
            return self.load(artifact.artifact_id)
        temporary = Path(tempfile.mkdtemp(prefix=".artifact-", dir=self.root))
        try:
            for name, content in files.items():
                path = temporary / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            (temporary / "manifest.json").write_text(artifact.manifest_json, encoding="utf-8")
            try:
                os.rename(temporary, destination)
            except OSError:
                if not destination.exists():
                    raise
                return self.load(artifact.artifact_id)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return artifact

    def load(self, artifact_id):
        folder = self.path(artifact_id)
        artifact = self.entity((folder / "manifest.json").read_text(encoding="utf-8"))
        if artifact.artifact_id != artifact_id:
            raise ValueError("Artifact manifest fingerprint mismatch")
        for name, checksum in artifact.manifest["files"].items():
            path = folder / name
            if not path.resolve().is_relative_to(folder.resolve()) or path.is_symlink():
                raise ValueError("Artifact members must remain inside their bundle")
            if sha256(path.read_bytes()).hexdigest() != checksum:
                raise ValueError("Artifact file fingerprint mismatch")
        return artifact

    def export(self, artifact_id):
        artifact = self.load(artifact_id)
        output = io.BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", artifact.manifest_json)
            for name in sorted(artifact.manifest["files"]):
                archive.writestr(name, (self.path(artifact_id) / name).read_bytes())
        return ExportedArtifact(output.getvalue(), f"{self.task}-{artifact_id}.zip")

    def list(self):
        found = {}
        candidates = [(path, False) for path in self.root.glob('*')]
        candidates += [(path, True) for path in self.base_root.glob('*')]
        for folder, legacy in candidates:
            if not re.fullmatch('[0-9a-f]{64}', folder.name) or not folder.is_dir() or folder.is_symlink(): continue
            if legacy:
                try:
                    if json.loads((folder / 'manifest.json').read_text()).get('task') != self.task: continue
                except (ValueError, OSError):
                    continue  # An unscoped damaged legacy folder cannot be attributed to a task safely.
            try:
                artifact = self.load(folder.name)
                found[folder.name] = dict(artifact_id=artifact.artifact_id, manifest=artifact.manifest, valid=True)
            except (ValueError, OSError):
                found[folder.name] = dict(artifact_id=folder.name, task=self.task, valid=False,
                                          error='Artifact bundle is damaged; delete and recreate it')
        return [found[key] for key in sorted(found)]

    def delete(self, artifact_id):
        folder = self.path(artifact_id)
        if not folder.is_dir(): raise FileNotFoundError("Artifact not found")
        if folder.is_symlink(): raise ValueError("Artifact directory must not be a symlink")
        # Scoped paths allow removing damaged bundles without requiring valid checksums.
        shutil.rmtree(folder)
