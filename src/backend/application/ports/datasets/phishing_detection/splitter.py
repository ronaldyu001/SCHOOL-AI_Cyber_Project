"""Contract for task-specific stratified split membership."""
from typing import Protocol, runtime_checkable
from domain.entities.datasets.phishing_detection import PhishingDetectionCleanedDataset, PhishingDetectionDatasetSplits, PhishingDetectionSplitPolicy

@runtime_checkable
class PhishingDetectionSplitterPort(Protocol):
    def split(self, dataset: PhishingDetectionCleanedDataset, policy: PhishingDetectionSplitPolicy) -> PhishingDetectionDatasetSplits: ...
