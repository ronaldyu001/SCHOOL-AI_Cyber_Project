"""Composition root for the dataset-scoped backend; no eager dataset loading."""
from pathlib import Path
from fastapi import FastAPI
from application.ports.preprocessing.malware_detection import MalwareDetectionPreprocessorPort
from application.ports.preprocessing.network_intrusion import NetworkIntrusionPreprocessorPort
from presentation.apis.datasets.malware_detection import create_router as malware_router
from presentation.apis.datasets.network_intrusion import create_router as network_router
from presentation.apis.datasets.phishing_detection import create_router as phishing_router


def create_app(data_root: Path | None = None, network_preprocessor: NetworkIntrusionPreprocessorPort | None = None,
               malware_preprocessor: MalwareDetectionPreprocessorPort | None = None) -> FastAPI:
    app = FastAPI(title="AI Cybersecurity Dataset API")
    root = Path(data_root) if data_root is not None else Path(__file__).resolve().parent / ".data"
    app.state.network_intrusion_datasets = {}
    app.state.phishing_detection_datasets = {}
    app.state.malware_detection_datasets = {}
    app.include_router(network_router(root, network_preprocessor, app.state.network_intrusion_datasets))
    app.include_router(phishing_router(root, app.state.phishing_detection_datasets))
    app.include_router(malware_router(root, malware_preprocessor, app.state.malware_detection_datasets))
    return app


app = create_app()
