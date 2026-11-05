"""Apply saved fitted statistics without fitting or deserializing Python objects."""
import numpy as np
from application.ports.preprocessing.network_intrusion import NetworkIntrusionPreprocessorPort
from domain.entities.datasets.network_intrusion import NetworkIntrusionPreprocessedDataset
from domain.entities.datasets.network_intrusion.schema import CATEGORICAL_FEATURES

class NetworkIntrusionArtifactPreprocessor(NetworkIntrusionPreprocessorPort):
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def transform(self, source, partition):
        s = self.artifacts.settings
        numeric = np.array([[np.nan if x is None else x for x in r.numeric] for r in partition.records], dtype=np.float32).reshape(-1, len(s["numeric_features"]))
        numeric[:] = np.where(np.isnan(numeric), s["fill_values"], numeric)
        numeric -= np.array(s["means"])
        numeric /= np.array(s["scales"])
        categorical = tuple(tuple(1 if value is None else s["category_maps"][column].get(value, 0)
                                  for column, value in zip(CATEGORICAL_FEATURES, r.categorical)) for r in partition.records)
        return NetworkIntrusionPreprocessedDataset(source, partition.row_ids,
            tuple(tuple(float(x) for x in row) for row in numeric), categorical,
            partition.labels, tuple(s["category_cardinalities"]))
