"""Model bundle upload, inspection, download, inference and release."""
from contextlib import asynccontextmanager, contextmanager
from threading import RLock
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse
from starlette.background import BackgroundTask
from safetensors import SafetensorError
from application.use_cases.models import ImportModel, PredictModel
from application.ports.progress import OperationCancelled
from domain.entities.models import FAMILIES, OUTPUT_CONTRACTS
from domain.entities.datasets.common import CyberTask
from infrastructure.adapters.models.baselines import BaselineUnavailable
from application.use_cases.models.baselines import ListBaselineModels
from infrastructure.adapters.models.store import ModelNotFound
from infrastructure.adapters.models.runtime import ModelRuntimeUnavailable
from infrastructure.adapters.preprocessing.artifact_store import ArtifactUnavailable

@contextmanager
def model_errors():
    try:
        yield
    except OperationCancelled:
        raise
    except (ModelNotFound, BaselineUnavailable) as error:
        raise HTTPException(404, str(error)) from error
    except (ModelRuntimeUnavailable, ArtifactUnavailable, ImportError) as error:
        raise HTTPException(503, str(error)) from error
    except (ValueError, RuntimeError, KeyError, TypeError, OverflowError, OSError, SafetensorError) as error:
        raise HTTPException(422, str(error)) from error


def describe(model):
    return dict(model_id=model.model_id, task=model.bundle.task.value,
                architecture=model.bundle.architecture, config=model.bundle.config,
                has_tokenizer=model.has_tokenizer, output_contract=model.bundle.output_contract)

class PredictRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: str = Field(min_length=1)
    preprocessed_id: str = Field(min_length=1)


def create_router(store, runtime, dataset_sessions, results=None, artifacts=None, storage_lock=None, baseline_catalog=None, baseline_loader=None, jobs=None):
    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            if jobs is not None: jobs.close()
            store.close()

    storage_lock = storage_lock or RLock()
    router = APIRouter(prefix='/models', tags=['models'], lifespan=lifespan)

    @router.get('/baselines')
    def list_baselines():
        if baseline_catalog is None: raise HTTPException(503, 'Baseline catalog is not configured')
        with model_errors():
            return ListBaselineModels(baseline_catalog).execute()

    @router.post('/baselines/{task}/load')
    def load_baseline(task: CyberTask):
        if baseline_loader is None: raise HTTPException(503, 'Baseline loader is not configured')
        with model_errors():
            model, reused = baseline_loader.execute(task.value)
            return dict(describe(model), reused=reused, baseline_task=task.value)

    @router.get('/capabilities')
    def capabilities():
        return {'format': 'zip', 'weights': 'safetensors', 'architectures': ['tabm', 'malconv', 'transformer'],
                'transformer_families': list(FAMILIES), 'output_contracts': OUTPUT_CONTRACTS,
                'optional_tokenizer': 'tokenizer/ containing tokenizer.json and saved special-token metadata'}

    @router.post('/upload', status_code=201,
                 openapi_extra={'requestBody': {'required': True, 'content': {'application/zip': {'schema': {'type': 'string', 'format': 'binary'}}}}})
    async def upload(request: Request):
        if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/zip':
            raise HTTPException(415, 'Send a ZIP body with Content-Type: application/zip')
        with SpooledTemporaryFile(max_size=8 * 1024**2, mode='w+b') as stream:
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 16 * 1024**3:
                    raise HTTPException(413, 'Model upload exceeds 16 GiB')
                await run_in_threadpool(stream.write, chunk)
            stream.seek(0)
            with model_errors():
                model = await run_in_threadpool(ImportModel(store, runtime).execute, stream)
                return describe(model)

    @router.get('')
    def list_models():
        return [describe(model) for model in store.list()]

    @router.get('/{model_id}')
    def inspect(model_id: str):
        with model_errors(), store.borrow(model_id) as (model, directory):
            result = describe(model)
            if model.bundle.architecture == 'transformer':
                import json
                result['transformer_config'] = json.loads((directory / 'config.json').read_text())
            return result

    @router.delete('/{model_id}', status_code=204)
    def delete(model_id: str):
        if jobs is not None: jobs.cancel_matching(kind="prediction", model_id=model_id)
        with model_errors():
            store.delete(model_id)
        return Response(status_code=204)

    @router.get('/{model_id}/download', response_class=StreamingResponse)
    def download(model_id: str):
        stream = SpooledTemporaryFile(max_size=8 * 1024**2, mode='w+b')
        try:
            with model_errors(), store.borrow(model_id) as (_, directory), ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
                for path in sorted(directory.rglob('*')):
                    if path.is_file():
                        archive.write(path, path.relative_to(directory).as_posix())
            stream.seek(0)
        except BaseException:
            stream.close()
            raise
        def chunks():
            try:
                while chunk := stream.read(64 * 1024):
                    yield chunk
            finally:
                stream.close()
        return StreamingResponse(chunks(), media_type='application/zip',
                                 headers={'Content-Disposition': f'attachment; filename="model-{model_id}.zip"'},
                                 background=BackgroundTask(stream.close))

    @router.post('/{model_id}/predict')
    def predict(model_id: str, body: PredictRequest):
        with model_errors():
            with store.borrow(model_id) as (model, _):
                sessions = dataset_sessions[model.bundle.task.value]
            session = sessions.get(body.dataset_id)
            if session is None:
                raise HTTPException(404, 'Dataset not found for this model task')
            with storage_lock, session.lock:
                if sessions.get(body.dataset_id) is not session:
                    raise HTTPException(404, "Dataset was unloaded before prediction started")
                dataset = session.preprocessed.get(body.preprocessed_id)
                if dataset is None:
                    raise HTTPException(404, 'Preprocessed result not found for this dataset')
                context = dict(dataset_id=body.dataset_id, preprocessed_id=body.preprocessed_id)
                if dataset.artifact_id is not None and artifacts is not None:
                    adapter = artifacts[dataset.source.task.value]
                    adapter.load(dataset.artifact_id)
                    context['artifact_directory'] = adapter.path(dataset.artifact_id)
                context['commit_guard'] = lambda: sessions.get(body.dataset_id) is session and session.preprocessed.get(body.preprocessed_id) is dataset
            return PredictModel(store, runtime, results).execute(model_id, dataset, context)

    @router.post('/{model_id}/predict/jobs', status_code=202)
    def start_prediction(model_id: str, body: PredictRequest):
        if jobs is None: raise HTTPException(503, 'Job service is not configured')
        model = next((m for m in store.list() if m.model_id == model_id), None)
        if model is None: raise HTTPException(404, 'Model not found')
        session = dataset_sessions[model.bundle.task.value].get(body.dataset_id)
        data = session.preprocessed.get(body.preprocessed_id) if session is not None else None
        if data is None: raise HTTPException(404, 'Preprocessed result not found for this dataset')
        with model_errors():
            return jobs.submit('prediction', dict(task=model.bundle.task.value, model_id=model_id,
                dataset_id=body.dataset_id, preprocessed_id=body.preprocessed_id, artifact_id=data.artifact_id),
                ('prediction', model_id, body.dataset_id, body.preprocessed_id), lambda: predict(model_id, body))

    return router
