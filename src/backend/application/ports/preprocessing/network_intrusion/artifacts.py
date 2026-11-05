"""Backend-owned creation and portable artifact storage contract."""
from typing import Protocol, runtime_checkable
from domain.entities.preprocessing import ExportedArtifact
from domain.entities.preprocessing.network_intrusion import NetworkIntrusionPreprocessingArtifacts
from domain.entities.datasets.network_intrusion import NetworkIntrusionPreparedDataset

@runtime_checkable
class NetworkIntrusionArtifactPort(Protocol):
    def create(self, prepared: NetworkIntrusionPreparedDataset, settings: dict | None = None) -> NetworkIntrusionPreprocessingArtifacts: ...
    def load(self, artifact_id: str) -> NetworkIntrusionPreprocessingArtifacts: ...
    def export(self, artifact_id: str) -> ExportedArtifact: ...
