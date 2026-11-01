from application.ports.datasets.network_intrusion import NetworkIntrusionDatasetPort
from domain.entities.datasets.common import DatasetSource
from domain.entities.datasets.network_intrusion import NetworkIntrusionLoadedDataset

class LoadNetworkIntrusionDataset:
    def __init__(self, dataset: NetworkIntrusionDatasetPort) -> None:
        self.dataset = dataset

    def execute(self, source: DatasetSource) -> NetworkIntrusionLoadedDataset:
        return NetworkIntrusionLoadedDataset(source, tuple(self.dataset.load_columns()), tuple(self.dataset.load_records()))
