from domain.entities.datasets.phishing_detection import (
    PhishingDetectionCleanedDataset, PhishingDetectionDatasetSplits,
    PhishingDetectionDatasetPartition, PhishingDetectionPreparedDataset,
)

class PreparePhishingDetectionDataset:
    def execute(self, dataset: PhishingDetectionCleanedDataset, split: PhishingDetectionDatasetSplits) -> PhishingDetectionPreparedDataset:
        by_id = {row.row_id: row for row in dataset.records}
        requested = set(split.train_row_ids + split.test_row_ids + split.eval_row_ids)
        if requested != set(by_id):
            raise ValueError("Split must include every cleaned record exactly once, without unknown IDs")
        def partition(ids: tuple[int, ...]) -> PhishingDetectionDatasetPartition:
            return PhishingDetectionDatasetPartition(tuple(by_id[row_id] for row_id in ids))
        return PhishingDetectionPreparedDataset(
            dataset.source, split, partition(split.train_row_ids), partition(split.test_row_ids), partition(split.eval_row_ids),
        )
