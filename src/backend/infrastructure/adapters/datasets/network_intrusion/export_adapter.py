"""ZIP serialization for task-specific dataset stages."""
from domain.entities.datasets.network_intrusion.schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES
from application.ports.datasets.export import ExportedDataset
from infrastructure.adapters.datasets.export import DatasetZIPExporter
from domain.entities.datasets.network_intrusion import (
    NetworkIntrusionLoadedDataset, NetworkIntrusionCleanedDataset, NetworkIntrusionDatasetSplits, NetworkIntrusionPreparedDataset, NetworkIntrusionPreprocessedDataset,
)

class NetworkIntrusionZIPExporter(DatasetZIPExporter):
    task = "network_intrusion"
    record_schema = {"numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES}

    def export_loaded(self, dataset: NetworkIntrusionLoadedDataset) -> ExportedDataset:
        return self._export(dataset, "loaded")

    def export_cleaned(self, dataset: NetworkIntrusionCleanedDataset) -> ExportedDataset:
        return self._export(dataset, "cleaned")

    def export_splits(self, dataset: NetworkIntrusionDatasetSplits) -> ExportedDataset:
        return self._export(dataset, "splits")

    def export_prepared(self, dataset: NetworkIntrusionPreparedDataset, partition: str) -> ExportedDataset:
        return self._export(dataset, "prepared", partition)

    def export_preprocessed(self, dataset: NetworkIntrusionPreprocessedDataset) -> ExportedDataset:
        return self._export(dataset, "preprocessed", dataset.partition)
