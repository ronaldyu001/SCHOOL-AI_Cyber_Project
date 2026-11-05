"""Validate download selection and delegate task-specific serialization."""
from application.ports.datasets.export import ExportedDataset
from application.ports.datasets.phishing_detection.export import PhishingDetectionExportPort
from domain.entities.datasets.phishing_detection import (
    PhishingDetectionLoadedDataset, PhishingDetectionCleanedDataset, PhishingDetectionDatasetSplits, PhishingDetectionPreparedDataset, PhishingDetectionPreprocessedDataset,
)

class ExportPhishingDetectionDataset:
    def __init__(self, exporter: PhishingDetectionExportPort) -> None:
        self.exporter = exporter

    def execute(self, dataset: PhishingDetectionLoadedDataset | PhishingDetectionCleanedDataset | PhishingDetectionDatasetSplits | PhishingDetectionPreparedDataset | PhishingDetectionPreprocessedDataset, partition: str | None = None) -> ExportedDataset:
        if isinstance(dataset, PhishingDetectionPreparedDataset):
            selected = "all" if partition is None else partition
            if selected not in ("train", "test", "eval", "all"):
                raise ValueError("Unknown dataset partition")
            return self.exporter.export_prepared(dataset, selected)
        if isinstance(dataset, PhishingDetectionPreprocessedDataset):
            if partition is not None and partition != dataset.partition:
                raise ValueError("Partition does not match the preprocessed result")
            return self.exporter.export_preprocessed(dataset)
        if partition is not None:
            raise ValueError("This stage is unsplit; omit partition")
        if isinstance(dataset, PhishingDetectionLoadedDataset):
            return self.exporter.export_loaded(dataset)
        if isinstance(dataset, PhishingDetectionCleanedDataset):
            return self.exporter.export_cleaned(dataset)
        if isinstance(dataset, PhishingDetectionDatasetSplits):
            return self.exporter.export_splits(dataset)
        raise ValueError("Unsupported dataset stage or cyber task")
