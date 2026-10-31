from typing import Protocol, runtime_checkable
from domain.entities.datasets.common import DatasetSource
from domain.entities.datasets.phishing_detection import PhishingDetectionDatasetPartition, PhishingDetectionPreprocessedDataset

@runtime_checkable
class PhishingDetectionPreprocessorPort(Protocol):
    def transform(self, source: DatasetSource, partition: PhishingDetectionDatasetPartition) -> PhishingDetectionPreprocessedDataset: ...
