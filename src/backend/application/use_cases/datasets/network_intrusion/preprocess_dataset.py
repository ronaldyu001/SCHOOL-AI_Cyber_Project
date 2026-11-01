from application.ports.preprocessing.network_intrusion import NetworkIntrusionPreprocessorPort
from domain.entities.datasets.network_intrusion import NetworkIntrusionPreparedDataset, NetworkIntrusionPreprocessedDataset

class PreprocessNetworkIntrusionDataset:
    def __init__(self, preprocessor: NetworkIntrusionPreprocessorPort) -> None:
        self.preprocessor = preprocessor

    def execute(self, dataset: NetworkIntrusionPreparedDataset) -> NetworkIntrusionPreprocessedDataset:
        result = self.preprocessor.transform(dataset.source, dataset.eval)
        if result.source != dataset.source or result.row_ids != dataset.eval.row_ids or result.labels != dataset.eval.labels:
            raise ValueError("Preprocessing must preserve eval source, row order, and labels")
        return result
