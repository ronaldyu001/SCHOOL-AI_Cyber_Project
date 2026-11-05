from pathlib import Path
import tempfile
from application.ports.preprocessing.phishing_detection.artifacts import PhishingDetectionArtifactPort
from domain.entities.preprocessing.phishing_detection import PhishingDetectionPreprocessingArtifacts
from ..artifact_store import JSONArtifactStore, ArtifactUnavailable

class PhishingDetectionArtifactAdapter(JSONArtifactStore, PhishingDetectionArtifactPort):
    entity = PhishingDetectionPreprocessingArtifacts
    task = "phishing_detection"

    def __init__(self, root, *, model_id="facebook/bart-large-mnli", revision="main", tokenizer_provider=None):
        super().__init__(root)
        self.model_id, self.revision = model_id, revision
        self.tokenizer_provider = tokenizer_provider

    def tokenizer(self):
        if self.tokenizer_provider is not None:
            return self.tokenizer_provider()
        from huggingface_hub import snapshot_download
        from transformers import AutoTokenizer
        try:
            folder = snapshot_download(self.model_id, revision=self.revision,
                cache_dir=str(self.root / ".tokenizer-cache"),
                allow_patterns=["tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "special_tokens_map.json", "config.json"])
            tokenizer = AutoTokenizer.from_pretrained(folder, local_files_only=True, trust_remote_code=False)
            return tokenizer, Path(folder).name
        except (OSError, ValueError) as error:
            raise ArtifactUnavailable("Tokenizer is unavailable; check connectivity or populate its local cache") from error

    def create(self, prepared, settings=None):
        defaults = {"max_length": 1024, "padding": "max_length", "truncation": "only_first"}
        if settings and set(settings) - defaults.keys():
            raise ValueError("Unknown phishing preprocessing settings")
        defaults.update(settings or {})
        if type(defaults["max_length"]) is not int or not 16 <= defaults["max_length"] <= 1024:
            raise ValueError("Tokenizer length must be between 16 and 1024")
        if defaults["padding"] != "max_length" or defaults["truncation"] != "only_first":
            raise ValueError("Unsupported tokenizer padding/truncation")
        tokenizer, revision = self.tokenizer()
        defaults.update({"tokenizer_id": self.model_id, "tokenizer_revision": revision,
                         "candidate_labels": ["phishing email", "legitimate email"],
                         "hypothesis_template": "This example is {}.",
                         "vocabulary_size": len(tokenizer),
                         "special_token_ids": {name: getattr(tokenizer, name + "_token_id")
                                               for name in ("pad", "bos", "eos", "unk")}})
        with tempfile.TemporaryDirectory() as directory:
            tokenizer.save_pretrained(directory)
            files = {"tokenizer/" + p.name: p.read_bytes() for p in Path(directory).iterdir() if p.is_file()}
        return self.save(prepared, defaults, files)

    def load_tokenizer(self, artifacts):
        from transformers import AutoTokenizer
        self.load(artifacts.artifact_id)
        return AutoTokenizer.from_pretrained(self.path(artifacts.artifact_id) / "tokenizer", local_files_only=True, trust_remote_code=False)
