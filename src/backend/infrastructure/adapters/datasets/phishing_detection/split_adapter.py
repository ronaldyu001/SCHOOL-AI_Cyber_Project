from application.ports.datasets.phishing_detection import PhishingDetectionSplitterPort
"""Replicate both stratified notebook splits without sorting source rows."""
from domain.entities.datasets.phishing_detection import (
    PhishingDetectionCleanedDataset, PhishingDetectionDatasetSplits, PhishingDetectionSplitPolicy,
)

class PhishingDetectionSklearnSplitter(PhishingDetectionSplitterPort):
    def split(self, dataset: PhishingDetectionCleanedDataset, policy: PhishingDetectionSplitPolicy = PhishingDetectionSplitPolicy()) -> PhishingDetectionDatasetSplits:
        from sklearn.model_selection import train_test_split
        ids = [row.row_id for row in dataset.records]
        labels = [int(row.label) for row in dataset.records]
        train, holdout, _, holdout_labels = train_test_split(
            ids, labels, train_size=policy.train_fraction, random_state=policy.seed, stratify=labels,
        )
        test, evaluation = train_test_split(
            holdout, train_size=policy.holdout_test_fraction, random_state=policy.seed, stratify=holdout_labels,
        )
        return PhishingDetectionDatasetSplits(tuple(train), tuple(test), tuple(evaluation), policy)
