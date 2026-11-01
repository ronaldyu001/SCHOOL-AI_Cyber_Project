"""Coordinate split creation and reject incomplete adapter output."""
from application.ports.datasets.phishing_detection import PhishingDetectionSplitterPort
from domain.entities.datasets.phishing_detection import PhishingDetectionCleanedDataset, PhishingDetectionDatasetSplits, PhishingDetectionSplitPolicy

class CreatePhishingDetectionDatasetSplit:
    def __init__(self, splitter: PhishingDetectionSplitterPort) -> None:
        self.splitter = splitter

    def execute(self, dataset: PhishingDetectionCleanedDataset, policy: PhishingDetectionSplitPolicy = PhishingDetectionSplitPolicy()) -> PhishingDetectionDatasetSplits:
        split = self.splitter.split(dataset, policy)
        ids = split.train_row_ids + split.test_row_ids + split.eval_row_ids
        if set(ids) != {record.row_id for record in dataset.records} or split.policy != policy:
            raise ValueError("Splitter must preserve all records and the requested policy")
        return split
