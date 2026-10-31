"""Split membership, separate from materialized data partitions."""
from dataclasses import dataclass

@dataclass(frozen=True)
class NetworkIntrusionSplitPolicy:
    seed: int = 123
    train_fraction: float = 0.7
    holdout_test_fraction: float = 0.5

    def __post_init__(self) -> None:
        if not 0 < self.train_fraction < 1 or not 0 < self.holdout_test_fraction < 1:
            raise ValueError("Split fractions must be between zero and one")

@dataclass(frozen=True)
class NetworkIntrusionDatasetSplits:
    train_row_ids: tuple[int, ...]
    test_row_ids: tuple[int, ...]
    eval_row_ids: tuple[int, ...]
    policy: NetworkIntrusionSplitPolicy = NetworkIntrusionSplitPolicy()

    def __post_init__(self) -> None:
        ids = self.train_row_ids + self.test_row_ids + self.eval_row_ids
        if len(ids) != len(set(ids)):
            raise ValueError("Row IDs must be unique across all partitions")
