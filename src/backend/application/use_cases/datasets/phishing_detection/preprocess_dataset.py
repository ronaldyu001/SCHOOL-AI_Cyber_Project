from dataclasses import replace
from application.ports.preprocessing.phishing_detection import PhishingDetectionPreprocessorPort
from domain.entities.datasets.phishing_detection import PhishingDetectionPreparedDataset, PhishingDetectionPreprocessedDataset

class PreprocessPhishingDetectionDataset:
    def __init__(self, preprocessor: PhishingDetectionPreprocessorPort) -> None:
        self.preprocessor = preprocessor

    def execute(self, dataset: PhishingDetectionPreparedDataset, partition: str = "eval") -> PhishingDetectionPreprocessedDataset:
        if partition not in ("train", "test", "eval"):
            raise ValueError("Unknown dataset partition")
        selected = getattr(dataset, partition)
        result = self.preprocessor.transform(dataset.source, selected)
        if result.source != dataset.source or result.row_ids != selected.row_ids or result.labels != selected.labels:
            raise ValueError(f"Preprocessing must preserve {partition} source, row order, and labels")
        return replace(result, partition=partition)
