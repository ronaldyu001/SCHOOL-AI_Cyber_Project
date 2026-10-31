"""Actual records in each partition, following the MSCS project pattern."""
from dataclasses import dataclass
from ..common import DatasetSource
from .records import NetworkIntrusionRecord
from .splits import NetworkIntrusionDatasetSplits

@dataclass(frozen=True)
class NetworkIntrusionDatasetPartition:
    records: tuple[NetworkIntrusionRecord, ...]

    @property
    def row_ids(self) -> tuple[int, ...]:
        return tuple(row.row_id for row in self.records)

    @property
    def labels(self) -> tuple[int, ...]:
        return tuple(int(row.label) for row in self.records)

@dataclass(frozen=True)
class NetworkIntrusionPreparedDataset:
    source: DatasetSource
    split: NetworkIntrusionDatasetSplits
    train: NetworkIntrusionDatasetPartition
    test: NetworkIntrusionDatasetPartition
    eval: NetworkIntrusionDatasetPartition

    def __post_init__(self) -> None:
        for partition, ids in ((self.train, self.split.train_row_ids), (self.test, self.split.test_row_ids), (self.eval, self.split.eval_row_ids)):
            if partition.row_ids != ids:
                raise ValueError("Partition records must match split membership and order")
