"""Coordinate split creation and reject incomplete adapter output."""
from application.ports.datasets.network_intrusion import NetworkIntrusionSplitterPort
from domain.entities.datasets.network_intrusion import NetworkIntrusionCleanedDataset, NetworkIntrusionDatasetSplits, NetworkIntrusionSplitPolicy

class CreateNetworkIntrusionDatasetSplit:
    def __init__(self, splitter: NetworkIntrusionSplitterPort) -> None:
        self.splitter = splitter

    def execute(self, dataset: NetworkIntrusionCleanedDataset, policy: NetworkIntrusionSplitPolicy = NetworkIntrusionSplitPolicy()) -> NetworkIntrusionDatasetSplits:
        split = self.splitter.split(dataset, policy)
        ids = split.train_row_ids + split.test_row_ids + split.eval_row_ids
        if set(ids) != {record.row_id for record in dataset.records} or split.policy != policy:
            raise ValueError("Splitter must preserve all records and the requested policy")
        return split
