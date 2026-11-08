"""Task-scoped artifact management independent of live dataset bindings."""
from fastapi import APIRouter, Response
from domain.entities.datasets.common import CyberTask
from presentation.apis.datasets.artifacts import artifact_errors


def create_router(adapters, sessions, lifecycle):
    router = APIRouter(prefix='/artifacts', tags=['stored artifacts'])

    @router.get('/{task}')
    def list_artifacts(task: CyberTask):
        with lifecycle.lock, artifact_errors():
            return adapters[task.value].list()

    @router.get('/{task}/{artifact_id}')
    def inspect(task: CyberTask, artifact_id: str):
        with lifecycle.lock, artifact_errors():
            artifact = adapters[task.value].load(artifact_id)
            return dict(artifact_id=artifact.artifact_id, manifest=artifact.manifest)

    @router.get('/{task}/{artifact_id}/download')
    def download(task: CyberTask, artifact_id: str):
        with lifecycle.lock, artifact_errors():
            exported = adapters[task.value].export(artifact_id)
            return Response(exported.content, media_type=exported.media_type,
                            headers={'Content-Disposition': f'attachment; filename="{exported.filename}"'})

    @router.delete('/{task}/{artifact_id}', status_code=204)
    def delete(task: CyberTask, artifact_id: str):
        if lifecycle.jobs is not None: lifecycle.jobs.invalidate(task=task.value, artifact_id=artifact_id)
        with lifecycle.lock, artifact_errors():
            lifecycle.delete_artifact(task.value, artifact_id)
        return Response(status_code=204)

    @router.delete('/{task}', status_code=204)
    def clear(task: CyberTask):
        if lifecycle.jobs is not None: lifecycle.jobs.invalidate(task=task.value)
        with lifecycle.lock, artifact_errors():
            for item in adapters[task.value].list():
                lifecycle.delete_artifact(task.value, item['artifact_id'])
        return Response(status_code=204)
    return router
