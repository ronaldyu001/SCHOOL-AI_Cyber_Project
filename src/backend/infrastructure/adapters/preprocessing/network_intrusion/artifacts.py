import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from application.ports.preprocessing.network_intrusion.artifacts import NetworkIntrusionArtifactPort
from domain.entities.preprocessing.network_intrusion import NetworkIntrusionPreprocessingArtifacts
from domain.entities.datasets.network_intrusion.schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES
from ..artifact_store import JSONArtifactStore

class NetworkIntrusionArtifactAdapter(JSONArtifactStore, NetworkIntrusionArtifactPort):
    entity = NetworkIntrusionPreprocessingArtifacts
    task = "network_intrusion"

    def create(self, prepared, settings=None):
        if settings:
            raise ValueError("Network preprocessing uses fixed median imputation and standard scaling")
        if not prepared.train.records:
            raise ValueError("Artifact fitting requires a nonempty training partition")
        numeric = np.array([[np.nan if x is None else x for x in r.numeric] for r in prepared.train.records], dtype=np.float32)
        imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        imputed = imputer.fit_transform(numeric)
        scaler = StandardScaler().fit(imputed)
        maps = {}
        for i, column in enumerate(CATEGORICAL_FEATURES):
            values = sorted({r.categorical[i] for r in prepared.train.records if r.categorical[i] is not None})
            maps[column] = {value: index + 2 for index, value in enumerate(values)}
        return self.save(prepared, {"numeric_features": list(NUMERIC_FEATURES), "categorical_features": list(CATEGORICAL_FEATURES),
            "imputer": "median", "all_missing_fill": 0, "scaler": "standard", "numeric_dtype": "float32",
            "fill_values": imputer.statistics_.tolist(), "means": scaler.mean_.tolist(), "scales": scaler.scale_.tolist(),
            "variances": scaler.var_.tolist(), "category_maps": maps,
            "category_cardinalities": [len(maps[c]) + 2 for c in CATEGORICAL_FEATURES],
            "unknown_category_id": 0, "missing_category_id": 1})
