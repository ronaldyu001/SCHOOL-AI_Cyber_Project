"""Drop missing/blank emails, normalize whitespace, reject label conflicts."""
import re
from domain.entities.datasets.phishing_detection import (
    Email, EmailLabel, PhishingDetectionLoadedDataset, PhishingDetectionCleanedDataset,
)
from domain.entities.datasets.phishing_detection.schema import TEXT_COLUMN, TARGET_COLUMN

class CleanPhishingDetectionDataset:
    def execute(self, dataset: PhishingDetectionLoadedDataset) -> PhishingDetectionCleanedDataset:
        text_index = dataset.columns.index(TEXT_COLUMN)
        label_index = dataset.columns.index(TARGET_COLUMN)
        seen: dict[str, EmailLabel] = {}
        records = []
        for row in dataset.records:
            text, label = row.values[text_index], row.values[label_index]
            if text is None or label is None:
                continue
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            try:
                parsed_label = EmailLabel(int(label))
            except (ValueError, TypeError) as error:
                raise ValueError(f"Invalid label at source row {row.row_id}") from error
            if text in seen:
                if seen[text] != parsed_label:
                    raise ValueError(f"Conflicting labels for email at source row {row.row_id}")
                continue
            seen[text] = parsed_label
            records.append(Email(row.row_id, text, parsed_label))
        if {record.label for record in records} != {0, 1}:
            raise ValueError("Cleaned dataset must contain both classes")
        return PhishingDetectionCleanedDataset(dataset.source, tuple(records), dataset.sample_count)
