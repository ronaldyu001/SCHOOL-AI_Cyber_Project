from .network_intrusion.artifact_adapter import NetworkIntrusionArtifactPreprocessor
from .malware_detection.byte_adapter import MalwareDetectionBytePreprocessor
from .phishing_detection.tokenizer_adapter import PhishingDetectionTokenizerPreprocessor

def preprocessor_for(adapter, artifacts):
    task = artifacts.task.value
    if task == "network_intrusion":
        return NetworkIntrusionArtifactPreprocessor(artifacts)
    if task == "malware_detection":
        s = artifacts.settings
        return MalwareDetectionBytePreprocessor(max_length=s["max_length"], byte_offset=s["byte_offset"], padding_token=s["padding_token"])
    return PhishingDetectionTokenizerPreprocessor(artifacts, adapter.load_tokenizer(artifacts))
