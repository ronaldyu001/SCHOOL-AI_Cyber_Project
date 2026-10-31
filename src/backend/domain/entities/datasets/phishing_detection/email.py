"""Actual raw and cleaned email records."""
from dataclasses import dataclass
from enum import IntEnum

class EmailLabel(IntEnum):
    LEGITIMATE = 0
    PHISHING = 1  # Positive examples in this combined corpus also include spam.

@dataclass(frozen=True)
class PhishingDetectionRawRecord:
    row_id: int
    values: tuple[str | None, ...]

@dataclass(frozen=True)
class Email:
    row_id: int
    text: str
    label: EmailLabel

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("Email text must be nonempty")
        if self.label not in (0, 1):
            raise ValueError("Expected legitimate (0) or phishing/spam (1)")
