from application.ports.datasets.phishing_detection import PhishingDetectionDatasetPort
from domain.entities.datasets.common import DatasetSource
from domain.entities.datasets.phishing_detection import PhishingDetectionLoadedDataset

class LoadPhishingDetectionDataset:
    def __init__(self, dataset: PhishingDetectionDatasetPort) -> None:
        self.dataset = dataset

    def execute(self, source: DatasetSource) -> PhishingDetectionLoadedDataset:
        return PhishingDetectionLoadedDataset(source, tuple(self.dataset.load_columns()), tuple(self.dataset.load_records()))
