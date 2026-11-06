"""Data-only model upload contracts. Model code and output semantics belong to the service."""
from dataclasses import dataclass
import json
import math
from domain.entities.datasets.common import CyberTask

ACTIVATIONS = ("ReLU", "GELU", "SiLU", "Tanh", "LeakyReLU", "ELU")
FAMILIES = ("bart", "bert", "roberta", "distilbert", "albert", "electra", "deberta", "deberta-v2", "xlm-roberta")
OUTPUT_CONTRACTS = {
    "transformer": {"kind": "nli_logits", "columns": ["contradiction", "neutral", "entailment"],
                    "prediction_labels": {"0": "legitimate", "1": "phishing"}},
    "malconv": {"kind": "binary_logit", "positive_label": 1,
                "prediction_labels": {"0": "benign", "1": "malware"}},
    "tabm": {"kind": "ensemble_binary_logits", "columns": ["normal", "attack"],
             "prediction_labels": {"0": "normal", "1": "attack"}},
}


def positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def config_for(architecture, values):
    if not isinstance(values, dict):
        raise ValueError("Model config must be an object")
    if architecture == "transformer":
        if values:
            raise ValueError("Transformer configuration belongs in config.json")
        return {}
    if architecture == "malconv":
        defaults = dict(embedding_dim=8, channels=128, kernel_size=512, stride=512,
                        hidden_size=128, activation="ReLU", padding_idx=256)
        integer_fields = ("embedding_dim", "channels", "kernel_size", "stride", "hidden_size")
    else:
        defaults = dict(n_blocks=3, d_block=512, k=32, dropout=0.1, activation="ReLU",
                        arch_type="tabm", n_num_features=16, cat_cardinalities=None, num_embeddings=None)
        integer_fields = ("n_blocks", "d_block", "k", "n_num_features")
    if set(values) - defaults.keys():
        raise ValueError("Unknown architecture configuration fields")
    defaults.update(values)
    for field in integer_fields:
        positive(defaults[field], field)
    if defaults["activation"] not in ACTIVATIONS:
        raise ValueError("Unsupported activation function")
    if architecture == "malconv":
        if type(defaults["padding_idx"]) is not int or defaults["padding_idx"] not in (0, 256):
            raise ValueError("padding_idx must be 0 or 256")
    else:
        if defaults["n_num_features"] != 16:
            raise ValueError("TabM requires the service's 16 numeric features")
        cards = defaults["cat_cardinalities"]
        if not isinstance(cards, list) or len(cards) != 5 or any(type(x) is not int or x < 2 for x in cards):
            raise ValueError("TabM requires five category cardinalities including reserved IDs")
        if defaults["arch_type"] not in ("tabm", "tabm-mini", "tabm-packed"):
            raise ValueError("Unsupported TabM variant")
        if type(defaults["dropout"]) not in (float, int) or not math.isfinite(defaults["dropout"]) or not 0 <= defaults["dropout"] < 1:
            raise ValueError("dropout must be in [0, 1)")
        embedding = defaults["num_embeddings"]
        if embedding is not None:
            if not isinstance(embedding, dict) or set(embedding) != {"bins", "d_embedding", "activation", "version"}:
                raise ValueError("Expected piecewise-linear embedding bins, d_embedding, activation, version")
            positive(embedding["d_embedding"], "d_embedding")
            if type(embedding["activation"]) is not bool or embedding["version"] not in ("A", "B"):
                raise ValueError("Invalid numerical embedding settings")
            bins = embedding["bins"]
            if not isinstance(bins, list) or len(bins) != 16:
                raise ValueError("Expected bins for each numeric feature")
            for edges in bins:
                if not isinstance(edges, list) or len(edges) < 2 or any(type(x) not in (float, int) or not math.isfinite(x) for x in edges):
                    raise ValueError("Embedding bins must be finite numeric lists")
                if any(a >= b for a, b in zip(edges, edges[1:])):
                    raise ValueError("Embedding bin edges must increase strictly")
    return defaults


@dataclass(frozen=True)
class ModelBundle:
    manifest_json: str

    def __post_init__(self):
        m = self.manifest
        if set(m) - {"schema_version", "task", "architecture", "config"} or m.get("schema_version") != 1:
            raise ValueError("Unsupported model manifest")
        expected = {"transformer": CyberTask.PHISHING_DETECTION, "malconv": CyberTask.MALWARE_DETECTION,
                    "tabm": CyberTask.NETWORK_INTRUSION}
        if m.get("architecture") not in expected or CyberTask(m.get("task")) != expected[m["architecture"]]:
            raise ValueError("Architecture does not match cyber task")
        config_for(m["architecture"], m.get("config", {}))

    @property
    def manifest(self):
        value = json.loads(self.manifest_json)
        if not isinstance(value, dict):
            raise ValueError("Model manifest must be an object")
        return value

    @property
    def task(self):
        return CyberTask(self.manifest["task"])

    @property
    def architecture(self):
        return self.manifest["architecture"]

    @property
    def config(self):
        return config_for(self.architecture, self.manifest.get("config", {}))

    @property
    def output_contract(self):
        return json.loads(json.dumps(OUTPUT_CONTRACTS[self.architecture]))


@dataclass(frozen=True)
class UploadedModel:
    model_id: str
    bundle: ModelBundle
    has_tokenizer: bool
