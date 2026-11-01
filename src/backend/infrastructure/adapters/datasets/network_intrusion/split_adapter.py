from application.ports.datasets.network_intrusion import NetworkIntrusionSplitterPort
"""Replicate both stratified notebook splits without sorting source rows."""
from domain.entities.datasets.network_intrusion import (
    NetworkIntrusionCleanedDataset, NetworkIntrusionDatasetSplits, NetworkIntrusionSplitPolicy,
)

class NetworkIntrusionSklearnSplitter(NetworkIntrusionSplitterPort):
    def split(self, dataset: NetworkIntrusionCleanedDataset, policy: NetworkIntrusionSplitPolicy = NetworkIntrusionSplitPolicy()) -> NetworkIntrusionDatasetSplits:
        from sklearn.model_selection import train_test_split
        ids = [row.row_id for row in dataset.records]
        labels = [int(row.label) for row in dataset.records]
        train, holdout, _, holdout_labels = train_test_split(
            ids, labels, train_size=policy.train_fraction, random_state=policy.seed, stratify=labels,
        )
        test, evaluation = train_test_split(
            holdout, train_size=policy.holdout_test_fraction, random_state=policy.seed, stratify=holdout_labels,
        )
        return NetworkIntrusionDatasetSplits(tuple(train), tuple(test), tuple(evaluation), policy)
