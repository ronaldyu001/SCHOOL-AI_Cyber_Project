"""Contract for task-specific stratified split membership."""
from typing import Protocol, runtime_checkable
from domain.entities.datasets.network_intrusion import NetworkIntrusionCleanedDataset, NetworkIntrusionDatasetSplits, NetworkIntrusionSplitPolicy

@runtime_checkable
class NetworkIntrusionSplitterPort(Protocol):
    def split(self, dataset: NetworkIntrusionCleanedDataset, policy: NetworkIntrusionSplitPolicy) -> NetworkIntrusionDatasetSplits: ...
