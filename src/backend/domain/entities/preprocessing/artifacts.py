"""Immutable, portable preprocessing contracts. No fitting or storage here."""
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from domain.entities.datasets.common import CyberTask


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class PreprocessingArtifacts:
    manifest_json: str

    def __post_init__(self):
        manifest = self.manifest
        if manifest.get("schema_version") != 1:
            raise ValueError("Unsupported artifact schema version")
        CyberTask(manifest["task"])
        if not isinstance(manifest.get("settings"), dict) or not isinstance(manifest.get("files"), dict):
            raise ValueError("Artifact settings and file checksums are required")
        provenance = manifest.get("provenance", {})
        if not provenance.get("dataset_version") or not provenance.get("training_fingerprint"):
            raise ValueError("Artifact provenance is required")
        for name, digest in manifest["files"].items():
            if name.startswith("/") or "\\" in name or any(p in ("", ".", "..") for p in name.split("/")) or name == "manifest.json":
                raise ValueError("Invalid artifact member path")
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Expected SHA-256 file fingerprint")

    @property
    def manifest(self):
        value = json.loads(self.manifest_json)
        if not isinstance(value, dict):
            raise ValueError("Expected an artifact manifest object")
        return value

    @property
    def settings(self):
        return self.manifest["settings"]

    @property
    def artifact_id(self):
        return sha256(canonical(self.manifest).encode()).hexdigest()

    @property
    def task(self):
        return CyberTask(self.manifest["task"])


@dataclass(frozen=True)
class ExportedArtifact:
    content: bytes
    filename: str
    media_type: str = "application/zip"


def provenance(prepared):
    # Exclude executable contents: their verified hashes already identify bytes.
    rows = [dict(row_id=r.row_id, sha256=r.sha256, label=int(r.label)) if hasattr(r, "sha256") else asdict(r)
            for r in prepared.train.records]
    return {"dataset_version": prepared.source.version,
            "training_fingerprint": sha256(canonical(rows).encode()).hexdigest(),
            "training_sample_count": len(rows)}


def validate_preprocessing_reference(artifact_id, partition):
    if partition not in ("train", "test", "eval"):
        raise ValueError("Unknown preprocessing partition")
    if artifact_id is not None and (not isinstance(artifact_id, str) or len(artifact_id) != 64 or any(c not in "0123456789abcdef" for c in artifact_id)):
        raise ValueError("Expected an artifact SHA-256 ID")
