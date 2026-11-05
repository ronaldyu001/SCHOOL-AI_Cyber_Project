"""Backend-owned creation and portable artifact storage contract."""
from typing import Protocol, runtime_checkable
from domain.entities.preprocessing import ExportedArtifact
from domain.entities.preprocessing.phishing_detection import PhishingDetectionPreprocessingArtifacts
from domain.entities.datasets.phishing_detection import PhishingDetectionPreparedDataset

@runtime_checkable
class PhishingDetectionArtifactPort(Protocol):
    def create(self, prepared: PhishingDetectionPreparedDataset, settings: dict | None = None) -> PhishingDetectionPreprocessingArtifacts: ...
    def load(self, artifact_id: str) -> PhishingDetectionPreprocessingArtifacts: ...
    def export(self, artifact_id: str) -> ExportedArtifact: ...
