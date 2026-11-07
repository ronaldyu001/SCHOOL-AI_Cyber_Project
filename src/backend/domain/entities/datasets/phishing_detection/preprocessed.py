"""Cleaned text and optional candidate-paired tokenizer inputs."""
from dataclasses import dataclass
from ..common import DatasetSource
from domain.entities.preprocessing.artifacts import validate_preprocessing_reference

@dataclass(frozen=True)
class PhishingDetectionPreprocessedDataset:
    source: DatasetSource
    row_ids: tuple[int, ...]
    texts: tuple[str, ...]
    labels: tuple[int, ...]

    input_ids: tuple[tuple[tuple[int, ...], ...], ...] = ()
    attention_mask: tuple[tuple[tuple[int, ...], ...], ...] = ()
    candidate_labels: tuple[str, ...] = ()

    artifact_id: str | None = None
    partition: str = "eval"
    model_id: str | None = None
    token_type_ids: tuple[tuple[tuple[int, ...], ...], ...] = ()
    premise_masks: tuple[tuple[tuple[int, ...], ...], ...] = ()

    def __post_init__(self) -> None:
        validate_preprocessing_reference(self.artifact_id, self.partition)
        if not len(self.row_ids) == len(self.texts) == len(self.labels):
            raise ValueError("Texts, labels, and row IDs must align")
        if len(set(self.row_ids)) != len(self.row_ids):
            raise ValueError("Evaluation row IDs must be unique")
        if any(not isinstance(text, str) or not text.strip() for text in self.texts):
            raise ValueError("Evaluation texts must be nonempty")
        if any(label not in (0, 1) for label in self.labels):
            raise ValueError("Expected binary labels")

        if self.candidate_labels or self.input_ids or self.attention_mask:
            if len(self.candidate_labels) != 2 or len(self.input_ids) != len(self.row_ids) or len(self.attention_mask) != len(self.row_ids):
                raise ValueError("Token pairs and candidates must align with samples")
            for pairs, masks in zip(self.input_ids, self.attention_mask):
                if len(pairs) != 2 or len(masks) != 2:
                    raise ValueError("Expected one premise/hypothesis pair per candidate")
                for tokens, mask in zip(pairs, masks):
                    if not tokens or len(tokens) != len(mask) or any(type(t) is not int or t < 0 for t in tokens) or any(m not in (0, 1) for m in mask):
                        raise ValueError("Invalid token IDs or attention masks")

        if self.token_type_ids:
            if len(self.token_type_ids) != len(self.input_ids):
                raise ValueError("Token type IDs must align with tokenized samples")
            for groups, pairs in zip(self.token_type_ids, self.input_ids):
                if len(groups) != len(pairs) or any(len(group) != len(pair) or any(type(v) is not int or v < 0 for v in group) for group, pair in zip(groups, pairs)):
                    raise ValueError("Token type IDs must align with candidate pairs")

        if self.premise_masks:
            if len(self.premise_masks) != len(self.input_ids):
                raise ValueError("Premise masks must align with tokenized samples")
            for masks, pairs in zip(self.premise_masks, self.input_ids):
                if len(masks) != len(pairs) or any(len(mask) != len(pair) or any(v not in (0, 1) for v in mask) for mask, pair in zip(masks, pairs)):
                    raise ValueError("Premise masks must align with candidate pairs")
