"""Actual CSV records, preserving source order and column names."""
from dataclasses import dataclass
from ..common import CyberTask, DatasetSource
from .email import PhishingDetectionRawRecord
from .schema import TEXT_COLUMN, TARGET_COLUMN

@dataclass(frozen=True)
class PhishingDetectionLoadedDataset:
    source: DatasetSource
    columns: tuple[str, ...]
    records: tuple[PhishingDetectionRawRecord, ...]

    def __post_init__(self) -> None:
        if self.source.task != CyberTask.PHISHING_DETECTION:
            raise ValueError("Expected phishing detection source")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Column names must be unique")
        if not set((TEXT_COLUMN, TARGET_COLUMN)) <= set(self.columns):
            raise ValueError("Missing required phishing email columns")
        if any(len(row.values) != len(self.columns) for row in self.records):
            raise ValueError("Row width must match source columns")
        if len({row.row_id for row in self.records}) != len(self.records):
            raise ValueError("Source row IDs must be unique")

    @property
    def sample_count(self) -> int:
        return len(self.records)
