"""Persistent prediction and analysis contracts."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class PredictionRows:
    row_ids: tuple[int, ...]
    labels: tuple[int, ...]
    probabilities: tuple[float, ...]

    def __post_init__(self):
        if not len(self.row_ids) == len(self.labels) == len(self.probabilities):
            raise ValueError("Result rows, labels and probabilities must align")
        if len(set(self.row_ids)) != len(self.row_ids):
            raise ValueError("Result row IDs must be unique")
        if any(v not in (0, 1) for v in self.labels) or any(not isfinite(v) or not 0 <= v <= 1 for v in self.probabilities):
            raise ValueError("Expected binary labels and finite probabilities")
