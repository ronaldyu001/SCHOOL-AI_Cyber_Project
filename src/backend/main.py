"""Composition root for the dataset-scoped backend; no eager dataset loading."""
from infrastructure.adapters.preprocessing.network_intrusion.artifacts import NetworkIntrusionArtifactAdapter
from infrastructure.adapters.preprocessing.malware_detection.artifacts import MalwareDetectionArtifactAdapter
from infrastructure.adapters.preprocessing.phishing_detection.artifacts import PhishingDetectionArtifactAdapter
from infrastructure.adapters.models.store import ModelBundleStore
from infrastructure.adapters.models.runtime import ModelRuntime
from presentation.apis.models.routes import create_router as models_router
from infrastructure.adapters.results.store import ResultStore
from infrastructure.adapters.results.evaluation import ClassificationEvaluation
from infrastructure.adapters.results.explanations import CaptumExplanations
from infrastructure.adapters.results.lifecycle import StorageLifecycle
from presentation.apis.results.routes import create_router as results_router
from presentation.apis.results.artifacts import create_router as stored_artifacts_router
from functools import partial
from pathlib import Path
from fastapi import FastAPI
from application.ports.preprocessing.malware_detection import MalwareDetectionPreprocessorPort
from application.ports.preprocessing.network_intrusion import NetworkIntrusionPreprocessorPort
from presentation.apis.datasets.malware_detection import create_router as malware_router
from presentation.apis.datasets.network_intrusion import create_router as network_router
from presentation.apis.datasets.phishing_detection import create_router as phishing_router


def create_app(data_root: Path | None = None, network_preprocessor: NetworkIntrusionPreprocessorPort | None = None,
               malware_preprocessor: MalwareDetectionPreprocessorPort | None = None,
               artifact_root: Path | None = None, phishing_artifact_adapter=None, results_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="AI Cybersecurity Dataset API")
    root = Path(data_root) if data_root is not None else Path(__file__).resolve().parent / ".data"
    artifact_root = Path(artifact_root) if artifact_root is not None else Path(__file__).resolve().parent / ".artifacts"
    app.state.model_store = ModelBundleStore()
    app.state.model_runtime = ModelRuntime()
    app.state.preprocessing_artifact_root = artifact_root
    app.state.network_intrusion_datasets = {}
    app.state.phishing_detection_datasets = {}
    app.state.malware_detection_datasets = {}
    results_root = Path(results_root) if results_root is not None else Path(__file__).resolve().parent / ".results"
    results = ResultStore(results_root)
    app.state.result_store = results
    artifacts = {
        "network_intrusion": NetworkIntrusionArtifactAdapter(artifact_root),
        "malware_detection": MalwareDetectionArtifactAdapter(artifact_root),
        "phishing_detection": phishing_artifact_adapter or PhishingDetectionArtifactAdapter(artifact_root),
    }
    app.state.artifact_adapters = artifacts
    sessions = {
        "network_intrusion": app.state.network_intrusion_datasets,
        "malware_detection": app.state.malware_detection_datasets,
        "phishing_detection": app.state.phishing_detection_datasets,
    }
    lifecycle = StorageLifecycle(results, artifacts, sessions)
    app.state.storage_lifecycle = lifecycle
    app.include_router(network_router(root, network_preprocessor, sessions['network_intrusion'],
        artifact_adapter=None if network_preprocessor else artifacts['network_intrusion'],
        cleanup=partial(lifecycle.cleanup, 'network_intrusion'), storage_lock=results.lock,
        delete_artifact=partial(lifecycle.delete_artifact, 'network_intrusion')))
    app.include_router(phishing_router(root, sessions['phishing_detection'], artifact_adapter=artifacts['phishing_detection'],
        model_store=app.state.model_store, model_runtime=app.state.model_runtime,
        cleanup=partial(lifecycle.cleanup, 'phishing_detection'), storage_lock=results.lock,
        delete_artifact=partial(lifecycle.delete_artifact, 'phishing_detection')))
    app.include_router(malware_router(root, malware_preprocessor, sessions['malware_detection'],
        artifact_adapter=None if malware_preprocessor else artifacts['malware_detection'],
        cleanup=partial(lifecycle.cleanup, 'malware_detection'), storage_lock=results.lock,
        delete_artifact=partial(lifecycle.delete_artifact, 'malware_detection')))
    app.include_router(models_router(app.state.model_store, app.state.model_runtime, sessions,
        results=results, artifacts=artifacts, storage_lock=results.lock))
    app.include_router(results_router(results, ClassificationEvaluation(), CaptumExplanations(app.state.model_runtime)))
    app.include_router(stored_artifacts_router(artifacts, sessions, lifecycle))
    return app


app = create_app()
