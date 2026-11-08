"""Persistent results and graph-ready evaluation / Captum analysis endpoints."""
from contextlib import contextmanager
import json
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from domain.entities.datasets.common import CyberTask
from domain.entities.results import PredictionOutcome
from application.use_cases.results.analyze import AnalyzeResult
from infrastructure.adapters.results.store import ResultNotFound
from presentation.apis.models.routes import model_errors

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    explain: bool = False
    outcome: PredictionOutcome | None = None
    row_ids: list[int] | None = Field(default=None, min_length=1, max_length=2000)
    sample_count: int = Field(default=4, ge=1, le=2000, strict=True)
    n_steps: int = Field(default=24, ge=2, le=512, strict=True)
    internal_batch_size: int = Field(default=2, ge=1, le=64, strict=True)
    n_repeats: int = Field(default=5, ge=1, le=100, strict=True)
    seed: int = Field(default=123, ge=0, le=4294967295, strict=True)
    include_byte_attributions: bool = False

@contextmanager
def result_errors():
    try:
        with model_errors():
            yield
    except ResultNotFound as error:
        raise HTTPException(404, str(error)) from error


def create_router(store, evaluation, explanations, jobs=None):
    router = APIRouter(prefix='/results', tags=['results and analysis'])

    @router.get('/{task}')
    def list_results(task: CyberTask, dataset_id: str | None = None):
        return [m for m in store.list(task) if dataset_id is None or m['dataset_id'] == dataset_id]

    @router.delete('/{task}', status_code=204)
    def clear_results(task: CyberTask):
        if jobs is not None: jobs.invalidate(task=task.value, kind="analysis")
        store.clear(task)
        return Response(status_code=204)

    @router.get('/{task}/{result_id}')
    def inspect(task: CyberTask, result_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=1000)):
        with result_errors(), store.borrow(task, result_id) as (directory, metadata):
            rows = store.rows(directory)
            return dict(metadata=metadata, total=metadata['sample_count'], offset=offset, limit=limit,
                        rows={key: value[offset:offset+limit] for key, value in rows.items()})

    @router.delete('/{task}/{result_id}', status_code=204)
    def delete(task: CyberTask, result_id: str):
        if jobs is not None: jobs.invalidate(task=task.value, result_id=result_id)
        with result_errors(): store.delete(task, result_id)
        return Response(status_code=204)

    @router.post('/{task}/{result_id}/analysis', status_code=201)
    def analyze(task: CyberTask, result_id: str, body: AnalysisRequest):
        with result_errors():
            return AnalyzeResult(store, evaluation, explanations).execute(task.value, result_id, body.model_dump(mode="json"))

    @router.post('/{task}/{result_id}/analysis/jobs', status_code=202)
    def start_analysis(task: CyberTask, result_id: str, body: AnalysisRequest):
        if jobs is None: raise HTTPException(503, 'Job service is not configured')
        with result_errors():
            metadata = store.metadata(task, result_id)
            return jobs.submit('analysis', dict(task=task.value, result_id=result_id,
                dataset_id=metadata.get('dataset_id'), artifact_id=metadata.get('artifact_id')),
                ('analysis', task.value, result_id, body.model_dump_json()), lambda: analyze(task, result_id, body))

    @router.get('/{task}/{result_id}/analysis')
    def list_analysis(task: CyberTask, result_id: str):
        with result_errors(), store.borrow(task, result_id) as (directory, _):
            values = [json.loads(path.read_text()) for path in sorted((directory / 'analyses').glob('*.json'))]
            return [{key: value[key] for key in ('analysis_id', 'created_at', 'parameters')} for value in values]

    @router.get('/{task}/{result_id}/analysis/{analysis_id}')
    def inspect_analysis(task: CyberTask, result_id: str, analysis_id: str):
        with result_errors(), store.borrow(task, result_id) as (directory, _):
            return json.loads(store.analysis_path(directory, analysis_id).read_text())

    @router.delete('/{task}/{result_id}/analysis/{analysis_id}', status_code=204)
    def delete_analysis(task: CyberTask, result_id: str, analysis_id: str):
        with result_errors(), store.borrow(task, result_id) as (directory, _):
            store.analysis_path(directory, analysis_id).unlink()
        return Response(status_code=204)

    @router.get('/{task}/{result_id}/download', response_class=StreamingResponse)
    def download(task: CyberTask, result_id: str):
        stream = SpooledTemporaryFile(max_size=8*1024**2, mode='w+b')
        try:
            with result_errors(), store.borrow(task, result_id) as (directory, _), ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
                for name in ('metadata.json', 'predictions.json'):
                    archive.write(directory / name, name)
                for path in sorted((directory / 'analyses').glob('*.json')):
                    archive.write(path, path.relative_to(directory).as_posix())
            stream.seek(0)
        except BaseException:
            stream.close()
            raise
        def chunks():
            try:
                while chunk := stream.read(64*1024): yield chunk
            finally: stream.close()
        return StreamingResponse(chunks(), media_type='application/zip',
            headers={'Content-Disposition': f'attachment; filename="{task.value}-{result_id}-results.zip"'},
            background=BackgroundTask(stream.close))
    return router
