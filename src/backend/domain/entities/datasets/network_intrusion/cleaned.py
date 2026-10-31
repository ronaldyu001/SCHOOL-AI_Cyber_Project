"""Selected, deduplicated records ready for partitioning."""
from dataclasses import dataclass
from ..common import DatasetSource, CyberTask
from .records import NetworkIntrusionRecord
from .schema import SCHEMA_VERSION

@dataclass(frozen=True)
class NetworkIntrusionCleanedDataset:
    source: DatasetSource
    records: tuple[NetworkIntrusionRecord, ...]
    loaded_sample_count: int
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.source.task != CyberTask.NETWORK_INTRUSION:
            raise ValueError("Dataset source task does not match entity")
        if self.loaded_sample_count < len(self.records):
            raise ValueError("Cleaned dataset cannot exceed source size")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unsupported schema version")
        if len({row.row_id for row in self.records}) != len(self.records):
            raise ValueError("Cleaned row IDs must be unique")

    @property
    def sample_count(self) -> int:
        return len(self.records)

    @property
    def removed_sample_count(self) -> int:
        return self.loaded_sample_count - self.sample_count
