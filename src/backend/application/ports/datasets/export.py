"""Download result shared by task export contracts; callers own stream cleanup."""
from dataclasses import dataclass
from typing import BinaryIO

@dataclass(frozen=True)
class ExportedDataset:
    stream: BinaryIO
    filename: str
    media_type: str = "application/zip"
