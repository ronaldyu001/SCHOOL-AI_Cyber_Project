"""Resolve immutable bundled sources and identify their exact contents."""
from hashlib import file_digest
from pathlib import Path
from domain.entities.datasets.common import CyberTask, DatasetSource

def bundled_source(root: Path, task: CyberTask, filename: str) -> tuple[Path, DatasetSource]:
    path = root / task.value / filename
    with path.open("rb") as source:
        checksum = file_digest(source, "sha256").hexdigest()
    return path, DatasetSource(filename, task, f"{task.value}/{filename}", f"sha256:{checksum}")
