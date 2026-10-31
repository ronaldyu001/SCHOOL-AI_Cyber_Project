from typing import Protocol, runtime_checkable
from domain.entities.datasets.common import DatasetSource
from domain.entities.datasets.network_intrusion import NetworkIntrusionDatasetPartition, NetworkIntrusionPreprocessedDataset

@runtime_checkable
class NetworkIntrusionPreprocessorPort(Protocol):
    def transform(self, source: DatasetSource, partition: NetworkIntrusionDatasetPartition) -> NetworkIntrusionPreprocessedDataset: ...
