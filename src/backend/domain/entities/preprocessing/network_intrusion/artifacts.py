from dataclasses import dataclass
from ..artifacts import PreprocessingArtifacts
from domain.entities.datasets.common import CyberTask

@dataclass(frozen=True)
class NetworkIntrusionPreprocessingArtifacts(PreprocessingArtifacts):
    def __post_init__(self):
        super().__post_init__()
        if self.task != CyberTask.NETWORK_INTRUSION:
            raise ValueError("Artifact task does not match entity")
        from domain.entities.datasets.network_intrusion.schema import NUMERIC_FEATURES, CATEGORICAL_FEATURES, validate_feature_order
        from math import isfinite
        s = self.settings
        if not {'categorical_features', 'means', 'imputer', 'scales', 'category_maps', 'scaler', 'fill_values', 'category_cardinalities', 'numeric_features'} <= s.keys():
            raise ValueError("Missing required artifact settings")
        validate_feature_order(tuple(s["numeric_features"]), tuple(s["categorical_features"]))
        if s["imputer"] != "median" or s["scaler"] != "standard":
            raise ValueError("Unsupported numeric preprocessing")
        for name in ("fill_values", "means", "scales"):
            if len(s[name]) != len(NUMERIC_FEATURES) or any(not isfinite(x) for x in s[name]):
                raise ValueError("Expected finite numeric statistics matching feature order")
        if any(x <= 0 for x in s["scales"]):
            raise ValueError("Scaler scales must be positive")
        if set(s["category_maps"]) != set(CATEGORICAL_FEATURES):
            raise ValueError("Category maps must match feature schema")
        if len(s["category_cardinalities"]) != len(CATEGORICAL_FEATURES):
            raise ValueError("Category cardinalities must match feature schema")
        for column, cardinality in zip(CATEGORICAL_FEATURES, s["category_cardinalities"]):
            mapping = s["category_maps"][column]
            if cardinality != len(mapping) + 2 or set(mapping.values()) != set(range(2, cardinality)):
                raise ValueError("Category mappings must reserve unseen/missing IDs 0/1")
