"""Transform with already-loaded checkpoint preprocessing; never fit here."""
from collections.abc import Mapping
import numpy as np
from application.ports.preprocessing.network_intrusion import NetworkIntrusionPreprocessorPort
from domain.entities.datasets.common import DatasetSource
from domain.entities.datasets.network_intrusion import NetworkIntrusionPreprocessedDataset, NetworkIntrusionDatasetPartition
from domain.entities.datasets.network_intrusion.schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES, validate_feature_order

class NetworkIntrusionCheckpointPreprocessor(NetworkIntrusionPreprocessorPort):
    def __init__(self, checkpoint: Mapping) -> None:
        validate_feature_order(tuple(checkpoint["num_cols"]), tuple(checkpoint["cat_cols"]))
        self.numeric_preprocessing = checkpoint["numeric_preprocessing"]
        self.category_maps = checkpoint["category_maps"]
        self.cardinalities = tuple(checkpoint["model_config"]["cat_cardinalities"])
        if len(self.cardinalities) != len(CATEGORICAL_FEATURES):
            raise ValueError("Checkpoint cardinalities must match categorical columns")
        for column, cardinality in zip(CATEGORICAL_FEATURES, self.cardinalities):
            mapping = self.category_maps[column]
            if len(mapping) + 2 != cardinality or set(mapping.values()) != set(range(2, cardinality)):
                raise ValueError("Checkpoint category maps must reserve IDs 0 and 1")

    def transform(self, source: DatasetSource, partition: NetworkIntrusionDatasetPartition) -> NetworkIntrusionPreprocessedDataset:
        records = partition.records
        if records:
            numeric = np.array([[np.nan if x is None else x for x in row.numeric] for row in records], dtype=np.float32)
            numeric = self.numeric_preprocessing.transform(numeric).astype(np.float32)
        else:
            numeric = np.empty((0, len(NUMERIC_FEATURES)), dtype=np.float32)
        categorical = tuple(tuple(
            1 if value is None else self.category_maps[column].get(value, 0)
            for column, value in zip(CATEGORICAL_FEATURES, row.categorical)
        ) for row in records)
        return NetworkIntrusionPreprocessedDataset(
            source, partition.row_ids, tuple(tuple(float(x) for x in row) for row in numeric),
            categorical, partition.labels, self.cardinalities,
        )
