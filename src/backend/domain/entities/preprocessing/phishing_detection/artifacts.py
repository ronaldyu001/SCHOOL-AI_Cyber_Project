from dataclasses import dataclass
from ..artifacts import PreprocessingArtifacts
from domain.entities.datasets.common import CyberTask

@dataclass(frozen=True)
class PhishingDetectionPreprocessingArtifacts(PreprocessingArtifacts):
    def __post_init__(self):
        super().__post_init__()
        if self.task != CyberTask.PHISHING_DETECTION:
            raise ValueError("Artifact task does not match entity")
        s = self.settings
        if not {'max_length', 'hypothesis_template', 'padding', 'truncation', 'tokenizer_revision', 'tokenizer_id', 'candidate_labels'} <= s.keys():
            raise ValueError("Missing required artifact settings")
        if type(s["max_length"]) is not int or not 16 <= s["max_length"] <= 1024:
            raise ValueError("Tokenizer length must be between 16 and 1024")
        if s["padding"] != "max_length" or s["truncation"] != "only_first":
            raise ValueError("Unsupported tokenizer padding/truncation")
        if len(s["candidate_labels"]) != 2 or len(set(s["candidate_labels"])) != 2:
            raise ValueError("Expected two distinct candidate labels")
        if not s["tokenizer_revision"] or not s["hypothesis_template"].count("{}") == 1:
            raise ValueError("Tokenizer revision and hypothesis template required")
        if not self.manifest["files"] or any(not name.startswith("tokenizer/") for name in self.manifest["files"]):
            raise ValueError("Tokenizer files are required")
