"""Framework-independent source rows and selected model inputs."""
from dataclasses import dataclass
from math import isfinite
from .schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES, NetworkIntrusionLabel

@dataclass(frozen=True)
class NetworkIntrusionRawRecord:
    row_id: int
    values: tuple[str | None, ...]

@dataclass(frozen=True)
class NetworkIntrusionRecord:
    row_id: int
    numeric: tuple[float | None, ...]
    categorical: tuple[str | None, ...]
    label: NetworkIntrusionLabel

    def __post_init__(self) -> None:
        if len(self.numeric) != len(NUMERIC_FEATURES) or len(self.categorical) != len(CATEGORICAL_FEATURES):
            raise ValueError("Record dimensions must match the fixed feature schema")
        if any(value is not None and not isfinite(value) for value in self.numeric):
            raise ValueError("Numeric values must be finite or missing")
        if self.label not in (0, 1):
            raise ValueError("Expected normal (0) or attack (1)")
