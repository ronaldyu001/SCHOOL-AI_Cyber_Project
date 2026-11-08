"""Persistent prediction and analysis contracts."""
from dataclasses import dataclass
from enum import Enum
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


class PredictionOutcome(str, Enum):
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    TRUE_NEGATIVE = "true_negative"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
            value = {"tp": "true_positive", "fp": "false_positive",
                     "fn": "false_negative", "tn": "true_negative"}.get(value, value)
            return next((item for item in cls if item.value == value), None)
        return None

    @classmethod
    def from_labels(cls, actual, predicted):
        return {(1, 1): cls.TRUE_POSITIVE, (0, 1): cls.FALSE_POSITIVE,
                (1, 0): cls.FALSE_NEGATIVE, (0, 0): cls.TRUE_NEGATIVE}[(actual, predicted)]
