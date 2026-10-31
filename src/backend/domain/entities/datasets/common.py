"""Shared dataset metadata. Payloads remain in infrastructure-managed artifacts."""
from dataclasses import dataclass
from enum import Enum

class CyberTask(str, Enum):
    NETWORK_INTRUSION = "network_intrusion"
    MALWARE_DETECTION = "malware_detection"
    PHISHING_DETECTION = "phishing_detection"

@dataclass(frozen=True)
class DatasetSource:
    dataset_id: str
    task: CyberTask
    artifact_id: str
    version: str

@dataclass(frozen=True)
class LoadedDataset:
    source: DatasetSource
    artifact_id: str
    sample_count: int

@dataclass(frozen=True)
class DatasetSplits:
    dataset: LoadedDataset
    train_artifact_id: str
    test_artifact_id: str
    eval_artifact_id: str
    seed: int = 42

@dataclass(frozen=True)
class PreprocessedDataset:
    splits: DatasetSplits
    train_artifact_id: str
    test_artifact_id: str
    eval_artifact_id: str
    preprocessor_artifact_id: str
