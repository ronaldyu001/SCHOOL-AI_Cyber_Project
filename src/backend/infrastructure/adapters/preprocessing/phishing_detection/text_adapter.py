"""Pass normalized text to the model, matching the zero-shot notebook.

No vectorizer, scaler, or vocabulary is fitted. The eventual model adapter owns
BART tokenization and truncation through its zero-shot classification pipeline.
"""
from application.ports.preprocessing.phishing_detection import PhishingDetectionPreprocessorPort
from domain.entities.datasets.common import DatasetSource
from domain.entities.datasets.phishing_detection import PhishingDetectionPreprocessedDataset, PhishingDetectionDatasetPartition

class PhishingDetectionTextPreprocessor(PhishingDetectionPreprocessorPort):
    def transform(self, source: DatasetSource, partition: PhishingDetectionDatasetPartition) -> PhishingDetectionPreprocessedDataset:
        return PhishingDetectionPreprocessedDataset(
            source, partition.row_ids, tuple(email.text for email in partition.records), partition.labels,
        )
