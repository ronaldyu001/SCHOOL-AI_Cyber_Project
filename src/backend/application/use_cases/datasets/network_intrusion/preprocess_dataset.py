from dataclasses import replace
from application.ports.preprocessing.network_intrusion import NetworkIntrusionPreprocessorPort
from domain.entities.datasets.network_intrusion import NetworkIntrusionPreparedDataset, NetworkIntrusionPreprocessedDataset

class PreprocessNetworkIntrusionDataset:
    def __init__(self, preprocessor: NetworkIntrusionPreprocessorPort) -> None:
        self.preprocessor = preprocessor

    def execute(self, dataset: NetworkIntrusionPreparedDataset, partition: str = "eval") -> NetworkIntrusionPreprocessedDataset:
        if partition not in ("train", "test", "eval"):
            raise ValueError("Unknown dataset partition")
        selected = getattr(dataset, partition)
        result = self.preprocessor.transform(dataset.source, selected)
        if result.source != dataset.source or result.row_ids != selected.row_ids or result.labels != selected.labels:
            raise ValueError(f"Preprocessing must preserve {partition} source, row order, and labels")
        return replace(result, partition=partition)
