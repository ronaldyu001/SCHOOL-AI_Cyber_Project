"""Actual transformed evaluation data; no pandas, NumPy, or tensor dependency."""
from dataclasses import dataclass
from math import isfinite
from ..common import DatasetSource
from .schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES, validate_feature_order

@dataclass(frozen=True)
class NetworkIntrusionPreprocessedDataset:
    source: DatasetSource
    row_ids: tuple[int, ...]
    numeric: tuple[tuple[float, ...], ...]
    categorical: tuple[tuple[int, ...], ...]
    labels: tuple[int, ...]
    category_cardinalities: tuple[int, ...]
    numeric_features: tuple[str, ...] = NUMERIC_FEATURES
    categorical_features: tuple[str, ...] = CATEGORICAL_FEATURES

    def __post_init__(self) -> None:
        validate_feature_order(self.numeric_features, self.categorical_features)
        if not len(self.row_ids) == len(self.numeric) == len(self.categorical) == len(self.labels):
            raise ValueError("Transformed features, labels, and IDs must align")
        if len(set(self.row_ids)) != len(self.row_ids):
            raise ValueError("Evaluation row IDs must be unique")
        if len(self.category_cardinalities) != len(CATEGORICAL_FEATURES) or any(type(n) is not int or n < 2 for n in self.category_cardinalities):
            raise ValueError("Expected checkpoint cardinalities including reserved IDs")
        if any(len(row) != len(NUMERIC_FEATURES) or any(not isfinite(x) for x in row) for row in self.numeric):
            raise ValueError("Expected finite numeric rows matching feature dimensions")
        if any(len(row) != len(CATEGORICAL_FEATURES) or any(type(x) is not int or not 0 <= x < n for x, n in zip(row, self.category_cardinalities)) for row in self.categorical):
            raise ValueError("Categorical IDs must fit checkpoint cardinalities")
        if any(label not in (0, 1) for label in self.labels):
            raise ValueError("Expected binary labels")
