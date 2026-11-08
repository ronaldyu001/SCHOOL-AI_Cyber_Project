from application.ports.progress import report_progress
from application.ports.preprocessing.phishing_detection import PhishingDetectionPreprocessorPort
from domain.entities.datasets.phishing_detection import PhishingDetectionPreprocessedDataset

class PhishingDetectionTokenizerPreprocessor(PhishingDetectionPreprocessorPort):
    def __init__(self, artifacts, tokenizer):
        self.artifacts, self.tokenizer = artifacts, tokenizer

    def transform(self, source, partition):
        settings = self.artifacts.settings
        ids, masks, types, premise = [], [], [], []
        report_progress("preprocessing", 0, len(partition.records))
        for index, record in enumerate(partition.records):
            report_progress("preprocessing", index, len(partition.records))
            candidates = settings["candidate_labels"]
            pairs = self.tokenizer([record.text] * len(candidates),
                [settings["hypothesis_template"].format(label) for label in candidates],
                max_length=settings["max_length"], padding=settings["padding"], truncation=settings["truncation"],
                return_attention_mask=True)
            premise.append(tuple(tuple(int(sid == 0) for sid in pairs.sequence_ids(i)) for i in range(len(candidates))))
            ids.append(tuple(tuple(row) for row in pairs["input_ids"]))
            if "token_type_ids" in pairs:
                types.append(tuple(tuple(row) for row in pairs["token_type_ids"]))
            masks.append(tuple(tuple(row) for row in pairs["attention_mask"]))
        report_progress("preprocessing", len(partition.records), len(partition.records))
        return PhishingDetectionPreprocessedDataset(source, partition.row_ids,
            tuple(r.text for r in partition.records), partition.labels,
            tuple(ids), tuple(masks), tuple(settings["candidate_labels"]), token_type_ids=tuple(types), premise_masks=tuple(premise))
