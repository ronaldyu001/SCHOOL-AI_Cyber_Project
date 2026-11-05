"""ZIP serialization for task-specific dataset stages."""
from application.ports.datasets.export import ExportedDataset
from infrastructure.adapters.datasets.export import DatasetZIPExporter
from domain.entities.datasets.phishing_detection import (
    PhishingDetectionLoadedDataset, PhishingDetectionCleanedDataset, PhishingDetectionDatasetSplits, PhishingDetectionPreparedDataset, PhishingDetectionPreprocessedDataset,
)

class PhishingDetectionZIPExporter(DatasetZIPExporter):
    task = "phishing_detection"

    def export_loaded(self, dataset: PhishingDetectionLoadedDataset) -> ExportedDataset:
        return self._export(dataset, "loaded")

    def export_cleaned(self, dataset: PhishingDetectionCleanedDataset) -> ExportedDataset:
        return self._export(dataset, "cleaned")

    def export_splits(self, dataset: PhishingDetectionDatasetSplits) -> ExportedDataset:
        return self._export(dataset, "splits")

    def export_prepared(self, dataset: PhishingDetectionPreparedDataset, partition: str) -> ExportedDataset:
        return self._export(dataset, "prepared", partition)

    def export_preprocessed(self, dataset: PhishingDetectionPreprocessedDataset) -> ExportedDataset:
        return self._export(dataset, "preprocessed", dataset.partition)
