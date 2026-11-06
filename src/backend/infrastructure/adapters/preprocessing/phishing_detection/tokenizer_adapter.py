from application.ports.preprocessing.phishing_detection import PhishingDetectionPreprocessorPort
from domain.entities.datasets.phishing_detection import PhishingDetectionPreprocessedDataset

class PhishingDetectionTokenizerPreprocessor(PhishingDetectionPreprocessorPort):
    def __init__(self, artifacts, tokenizer):
        self.artifacts, self.tokenizer = artifacts, tokenizer

    def transform(self, source, partition):
        settings = self.artifacts.settings
        ids, masks, types = [], [], []
        for record in partition.records:
            candidates = settings["candidate_labels"]
            pairs = self.tokenizer([record.text] * len(candidates),
                [settings["hypothesis_template"].format(label) for label in candidates],
                max_length=settings["max_length"], padding=settings["padding"], truncation=settings["truncation"],
                return_attention_mask=True)
            ids.append(tuple(tuple(row) for row in pairs["input_ids"]))
            if "token_type_ids" in pairs:
                types.append(tuple(tuple(row) for row in pairs["token_type_ids"]))
            masks.append(tuple(tuple(row) for row in pairs["attention_mask"]))
        return PhishingDetectionPreprocessedDataset(source, partition.row_ids,
            tuple(r.text for r in partition.records), partition.labels,
            tuple(ids), tuple(masks), tuple(settings["candidate_labels"]), token_type_ids=tuple(types))
