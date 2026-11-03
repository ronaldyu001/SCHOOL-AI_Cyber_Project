"""Split membership, separate from materialized data partitions."""
from dataclasses import dataclass
from math import isclose, isfinite

@dataclass(frozen=True)
class PhishingDetectionSplitPolicy:
    seed: int = 123
    train_fraction: float = 0.7
    test_fraction: float = 0.15
    eval_fraction: float = 0.15

    def __post_init__(self) -> None:
        fractions = (self.train_fraction, self.test_fraction, self.eval_fraction)
        if any(not isfinite(value) or not 0 < value < 1 for value in fractions):
            raise ValueError("Split fractions must be between zero and one")
        if not isclose(sum(fractions), 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("Train, test, and eval fractions must sum to one")

@dataclass(frozen=True)
class PhishingDetectionDatasetSplits:
    train_row_ids: tuple[int, ...]
    test_row_ids: tuple[int, ...]
    eval_row_ids: tuple[int, ...]
    policy: PhishingDetectionSplitPolicy = PhishingDetectionSplitPolicy()

    def __post_init__(self) -> None:
        ids = self.train_row_ids + self.test_row_ids + self.eval_row_ids
        if len(ids) != len(set(ids)):
            raise ValueError("Row IDs must be unique across all partitions")
