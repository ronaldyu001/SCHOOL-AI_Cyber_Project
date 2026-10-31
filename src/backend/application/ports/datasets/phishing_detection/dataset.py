from typing import Protocol, Sequence, runtime_checkable
from domain.entities.datasets.phishing_detection import PhishingDetectionRawRecord

@runtime_checkable
class PhishingDetectionDatasetPort(Protocol):
    def load_columns(self) -> Sequence[str]: ...
    def load_records(self) -> Sequence[PhishingDetectionRawRecord]: ...
