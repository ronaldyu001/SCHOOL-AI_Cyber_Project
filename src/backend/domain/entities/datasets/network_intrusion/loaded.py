"""Actual CSV records, preserving source order and column names."""
from dataclasses import dataclass
from ..common import CyberTask, DatasetSource
from .records import NetworkIntrusionRawRecord
from .schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET_COLUMN

@dataclass(frozen=True)
class NetworkIntrusionLoadedDataset:
    source: DatasetSource
    columns: tuple[str, ...]
    records: tuple[NetworkIntrusionRawRecord, ...]

    def __post_init__(self) -> None:
        if self.source.task != CyberTask.NETWORK_INTRUSION:
            raise ValueError("Expected network intrusion source")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Column names must be unique")
        if not set((*NUMERIC_FEATURES, *CATEGORICAL_FEATURES, TARGET_COLUMN)) <= set(self.columns):
            raise ValueError("Missing required ToN_IoT columns")
        if any(len(row.values) != len(self.columns) for row in self.records):
            raise ValueError("Row width must match source columns")
        if len({row.row_id for row in self.records}) != len(self.records):
            raise ValueError("Source row IDs must be unique")

    @property
    def sample_count(self) -> int:
        return len(self.records)
