"""Apply saved fitted statistics without fitting or deserializing Python objects."""
import numpy as np
from application.ports.progress import report_progress
from application.ports.preprocessing.network_intrusion import NetworkIntrusionPreprocessorPort
from domain.entities.datasets.network_intrusion import NetworkIntrusionPreprocessedDataset
from domain.entities.datasets.network_intrusion.schema import CATEGORICAL_FEATURES

class NetworkIntrusionArtifactPreprocessor(NetworkIntrusionPreprocessorPort):
    def __init__(self, artifacts):
        self.artifacts = artifacts

    def transform(self, source, partition):
        s = self.artifacts.settings
        report_progress("preprocessing", 0, len(partition.records))
        numeric = np.array([[np.nan if x is None else x for x in r.numeric] for r in partition.records], dtype=np.float32).reshape(-1, len(s["numeric_features"]))
        numeric[:] = np.where(np.isnan(numeric), s["fill_values"], numeric)
        numeric -= np.array(s["means"])
        numeric /= np.array(s["scales"])
        categorical = []
        for index, row in enumerate(partition.records):
            if index % 128 == 0: report_progress('preprocessing', index, len(partition.records))
            categorical.append(tuple(1 if value is None else s['category_maps'][column].get(value, 0)
                for column, value in zip(CATEGORICAL_FEATURES, row.categorical)))
        categorical = tuple(categorical)
        report_progress('preprocessing', len(partition.records), len(partition.records))
        return NetworkIntrusionPreprocessedDataset(source, partition.row_ids,
            tuple(tuple(float(x) for x in row) for row in numeric), categorical,
            partition.labels, tuple(s["category_cardinalities"]))
