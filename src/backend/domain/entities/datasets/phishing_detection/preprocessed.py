"""Evaluation text inputs ready for the model's zero-shot pipeline.

The notebook performs whitespace normalization during cleaning. Tokenization
belongs to the imported model's pipeline and is not fitted on this dataset.
"""
from dataclasses import dataclass
from ..common import DatasetSource

@dataclass(frozen=True)
class PhishingDetectionPreprocessedDataset:
    source: DatasetSource
    row_ids: tuple[int, ...]
    texts: tuple[str, ...]
    labels: tuple[int, ...]

    def __post_init__(self) -> None:
        if not len(self.row_ids) == len(self.texts) == len(self.labels):
            raise ValueError("Texts, labels, and row IDs must align")
        if len(set(self.row_ids)) != len(self.row_ids):
            raise ValueError("Evaluation row IDs must be unique")
        if any(not isinstance(text, str) or not text.strip() for text in self.texts):
            raise ValueError("Evaluation texts must be nonempty")
        if any(label not in (0, 1) for label in self.labels):
            raise ValueError("Expected binary labels")
