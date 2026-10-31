from typing import Protocol, Sequence, runtime_checkable
from domain.entities.datasets.network_intrusion import NetworkIntrusionRawRecord

@runtime_checkable
class NetworkIntrusionDatasetPort(Protocol):
    def load_columns(self) -> Sequence[str]: ...
    def load_records(self) -> Sequence[NetworkIntrusionRawRecord]: ...
