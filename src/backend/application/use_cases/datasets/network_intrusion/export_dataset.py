"""Validate download selection and delegate task-specific serialization."""
from application.ports.datasets.export import ExportedDataset
from application.ports.datasets.network_intrusion.export import NetworkIntrusionExportPort
from domain.entities.datasets.network_intrusion import (
    NetworkIntrusionLoadedDataset, NetworkIntrusionCleanedDataset, NetworkIntrusionDatasetSplits, NetworkIntrusionPreparedDataset, NetworkIntrusionPreprocessedDataset,
)

class ExportNetworkIntrusionDataset:
    def __init__(self, exporter: NetworkIntrusionExportPort) -> None:
        self.exporter = exporter

    def execute(self, dataset: NetworkIntrusionLoadedDataset | NetworkIntrusionCleanedDataset | NetworkIntrusionDatasetSplits | NetworkIntrusionPreparedDataset | NetworkIntrusionPreprocessedDataset, partition: str | None = None) -> ExportedDataset:
        if isinstance(dataset, NetworkIntrusionPreparedDataset):
            selected = "all" if partition is None else partition
            if selected not in ("train", "test", "eval", "all"):
                raise ValueError("Unknown dataset partition")
            return self.exporter.export_prepared(dataset, selected)
        if isinstance(dataset, NetworkIntrusionPreprocessedDataset):
            if partition is not None and partition != dataset.partition:
                raise ValueError("Partition does not match the preprocessed result")
            return self.exporter.export_preprocessed(dataset)
        if partition is not None:
            raise ValueError("This stage is unsplit; omit partition")
        if isinstance(dataset, NetworkIntrusionLoadedDataset):
            return self.exporter.export_loaded(dataset)
        if isinstance(dataset, NetworkIntrusionCleanedDataset):
            return self.exporter.export_cleaned(dataset)
        if isinstance(dataset, NetworkIntrusionDatasetSplits):
            return self.exporter.export_splits(dataset)
        raise ValueError("Unsupported dataset stage or cyber task")
