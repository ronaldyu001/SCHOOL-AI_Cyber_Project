from application.ports.preprocessing.phishing_detection import PhishingDetectionPreprocessorPort
from domain.entities.datasets.phishing_detection import PhishingDetectionPreparedDataset, PhishingDetectionPreprocessedDataset

class PreprocessPhishingDetectionDataset:
    def __init__(self, preprocessor: PhishingDetectionPreprocessorPort) -> None:
        self.preprocessor = preprocessor

    def execute(self, dataset: PhishingDetectionPreparedDataset) -> PhishingDetectionPreprocessedDataset:
        result = self.preprocessor.transform(dataset.source, dataset.eval)
        if result.source != dataset.source or result.row_ids != dataset.eval.row_ids or result.labels != dataset.eval.labels:
            raise ValueError("Preprocessing must preserve eval source, row order, and labels")
        return result
