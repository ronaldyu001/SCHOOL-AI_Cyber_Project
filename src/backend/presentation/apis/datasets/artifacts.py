"""Dataset-owned artifact creation, inspection and portable ZIP downloads."""
from fastapi import HTTPException, Response
from application.use_cases.preprocessing import CreatePreprocessingArtifacts, ExportPreprocessingArtifacts
from presentation.apis.datasets.schemas import ArtifactRequest
from presentation.apis.datasets.errors import dataset_errors
from infrastructure.adapters.preprocessing.artifact_store import ArtifactUnavailable
from contextlib import contextmanager

@contextmanager
def artifact_errors():
    try:
        with dataset_errors():
            yield
    except ArtifactUnavailable as error:
        raise HTTPException(503, str(error)) from error


def get_artifact(session, adapter, prepared_id, artifact_id):
    if adapter is None:
        raise HTTPException(409, "Artifact service is not configured")
    if artifact_id not in session.artifact_bindings.get(prepared_id, set()):
        raise HTTPException(404, "Artifact does not belong to this prepared dataset")
    return adapter.load(artifact_id)


def add_artifact_routes(router, get_session, adapter):
    @router.post("/{dataset_id}/artifacts", status_code=201)
    def create_artifact(dataset_id: str, body: ArtifactRequest):
        session = get_session(dataset_id)
        with session.lock, artifact_errors():
            prepared = session.prepared.get(body.prepared_id)
            if prepared is None:
                raise HTTPException(404, "Prepared dataset not found for this dataset")
            if adapter is None:
                raise HTTPException(409, "Artifact service is not configured")
            artifact = CreatePreprocessingArtifacts(adapter).execute(prepared, body.settings)
            session.artifact_bindings.setdefault(body.prepared_id, set()).add(artifact.artifact_id)
            return {"artifact_id": artifact.artifact_id, "manifest": artifact.manifest}

    def owned_artifact(session, artifact_id):
        if not any(artifact_id in ids for ids in session.artifact_bindings.values()):
            raise HTTPException(404, "Artifact not found for this dataset")
        if adapter is None:
            raise HTTPException(409, "Artifact service is not configured")
        return adapter.load(artifact_id)

    @router.get("/{dataset_id}/artifacts/{artifact_id}")
    def inspect_artifact(dataset_id: str, artifact_id: str):
        session = get_session(dataset_id)
        with session.lock, artifact_errors():
            artifact = owned_artifact(session, artifact_id)
            return {"artifact_id": artifact.artifact_id, "manifest": artifact.manifest}

    @router.get("/{dataset_id}/artifacts/{artifact_id}/download")
    def download_artifact(dataset_id: str, artifact_id: str):
        session = get_session(dataset_id)
        with session.lock, artifact_errors():
            owned_artifact(session, artifact_id)
            exported = ExportPreprocessingArtifacts(adapter).execute(artifact_id)
            return Response(exported.content, media_type=exported.media_type,
                            headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'})


def check_input_budget(artifact, partition):
    if artifact.task.value == "network_intrusion":
        return
    settings = artifact.settings
    candidates = len(settings.get("candidate_labels", [None]))
    if len(partition.records) * settings["max_length"] * candidates > 32_000_000:
        raise ValueError("This partition exceeds the 32-million-token in-memory limit. Create an artifact with a shorter input length or use a smaller dataset.")
