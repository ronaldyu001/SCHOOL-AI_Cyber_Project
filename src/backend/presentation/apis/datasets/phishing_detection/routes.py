"""Dataset-only HTTP endpoints for phishing detection."""
from presentation.apis.datasets.resets import add_reset_routes
from presentation.apis.datasets.downloads import add_download_routes
from application.use_cases.datasets.phishing_detection.export_dataset import ExportPhishingDetectionDataset
from infrastructure.adapters.datasets.phishing_detection.export_adapter import PhishingDetectionZIPExporter
from presentation.apis.datasets.artifacts import add_artifact_routes, get_artifact, artifact_errors, check_input_budget
from infrastructure.adapters.preprocessing.artifact_factory import preprocessor_for
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query, Response
from application.use_cases.datasets.phishing_detection import (
    LoadPhishingDetectionDataset, CleanPhishingDetectionDataset,
    CreatePhishingDetectionDatasetSplit, PreparePhishingDetectionDataset,
    PreprocessPhishingDetectionDataset,
)
from domain.entities.datasets.common import CyberTask
from domain.entities.datasets.phishing_detection import (
    PhishingDetectionLoadedDataset, PhishingDetectionCleanedDataset,
    PhishingDetectionDatasetSplits, PhishingDetectionSplitPolicy,
    PhishingDetectionPreparedDataset, PhishingDetectionPreprocessedDataset,
)
from infrastructure.adapters.datasets.catalog import bundled_source
from infrastructure.adapters.datasets.phishing_detection import PhishingDetectionCSVAdapter, PhishingDetectionSklearnSplitter
from infrastructure.adapters.preprocessing.phishing_detection import PhishingDetectionTextPreprocessor
from presentation.apis.datasets.errors import dataset_errors
from presentation.apis.datasets.schemas import (
    SplitRequest, PrepareRequest, PreprocessRequest, SourceResponse, CleanResponse,
    SplitResponse, PrepareResponse, PreprocessResponse, RecordsResponse,
)

@dataclass
class DatasetSession:
    loaded: PhishingDetectionLoadedDataset
    cleaned: PhishingDetectionCleanedDataset | None = None
    splits: dict[str, PhishingDetectionDatasetSplits] = field(default_factory=dict)
    prepared: dict[str, PhishingDetectionPreparedDataset] = field(default_factory=dict)
    artifact_bindings: dict[str, set[str]] = field(default_factory=dict)
    preprocessed: dict[str, PhishingDetectionPreprocessedDataset] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)


def create_router(data_root: Path, sessions: dict[str, DatasetSession] | None = None, artifact_adapter=None, model_store=None, model_runtime=None, cleanup=None, storage_lock=None, delete_artifact=None) -> APIRouter:
    storage_lock = storage_lock or RLock()
    router = APIRouter(prefix="/datasets/phishing_detection", tags=["phishing_detection datasets"])
    # Per-application memory, like the reference repo. No dataset reads at startup.
    sessions = {} if sessions is None else sessions

    def get_session(dataset_id: str) -> DatasetSession:
        session = sessions.get(dataset_id)
        if session is None:
            raise HTTPException(404, "Dataset not found; load it first")
        return session

    @router.post("/load", response_model=SourceResponse, status_code=201)
    def load_dataset() -> SourceResponse:
        with dataset_errors():
            path, source = bundled_source(data_root, CyberTask.PHISHING_DETECTION, "phishing_email.csv")
            loaded = LoadPhishingDetectionDataset(PhishingDetectionCSVAdapter(path)).execute(source)
        dataset_id = str(uuid4())
        with storage_lock:
            sessions[dataset_id] = DatasetSession(loaded)
        return SourceResponse(dataset_id=dataset_id, task=source.task.value, filename=path.name,
                              version=source.version, sample_count=loaded.sample_count, columns=list(loaded.columns))

    @router.post("/{dataset_id}/clean", response_model=CleanResponse)
    def clean_dataset(dataset_id: str) -> CleanResponse:
        session = get_session(dataset_id)
        with storage_lock, session.lock, dataset_errors():
            if session.cleaned is None:
                session.cleaned = CleanPhishingDetectionDataset().execute(session.loaded)
            cleaned = session.cleaned
            return CleanResponse(dataset_id=dataset_id, sample_count=cleaned.sample_count,
                                 removed_sample_count=cleaned.removed_sample_count, schema_version=cleaned.schema_version)

    @router.post("/{dataset_id}/splits", response_model=SplitResponse, status_code=201)
    def create_split(dataset_id: str, body: SplitRequest) -> SplitResponse:
        session = get_session(dataset_id)
        with storage_lock, session.lock, dataset_errors():
            if session.cleaned is None:
                raise HTTPException(409, "Clean the dataset before creating a split")
            policy = PhishingDetectionSplitPolicy(seed=body.seed, train_fraction=body.train_fraction,
                                                    test_fraction=body.test_fraction, eval_fraction=body.eval_fraction)
            split = CreatePhishingDetectionDatasetSplit(PhishingDetectionSklearnSplitter()).execute(session.cleaned, policy)
            split_id = str(uuid4())
            session.splits[split_id] = split
            return SplitResponse(dataset_id=dataset_id, split_id=split_id, seed=policy.seed,
                                 train_count=len(split.train_row_ids), test_count=len(split.test_row_ids), eval_count=len(split.eval_row_ids))

    @router.post("/{dataset_id}/prepare", response_model=PrepareResponse, status_code=201)
    def prepare_dataset(dataset_id: str, body: PrepareRequest) -> PrepareResponse:
        session = get_session(dataset_id)
        with storage_lock, session.lock, dataset_errors():
            split = session.splits.get(body.split_id)
            if split is None:
                raise HTTPException(404, "Split not found for this dataset")
            if session.cleaned is None:
                raise HTTPException(409, "Clean the dataset first")
            prepared = PreparePhishingDetectionDataset().execute(session.cleaned, split)
            prepared_id = str(uuid4())
            session.prepared[prepared_id] = prepared
            return PrepareResponse(dataset_id=dataset_id, split_id=body.split_id, prepared_id=prepared_id,
                                   train_count=len(prepared.train.records), test_count=len(prepared.test.records), eval_count=len(prepared.eval.records))

    @router.get("/{dataset_id}/prepared/{prepared_id}/{partition}", response_model=RecordsResponse)
    def partition_records(dataset_id: str, prepared_id: str, partition: Literal["train", "test", "eval"],
                          offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=1000)) -> RecordsResponse:
        session = get_session(dataset_id)
        with storage_lock, session.lock:
            prepared = session.prepared.get(prepared_id)
            if prepared is None:
                raise HTTPException(404, "Prepared dataset not found for this dataset")
            records = getattr(prepared, partition).records
            return RecordsResponse(total=len(records), offset=offset, limit=limit,
                                   records=[asdict(row) for row in records[offset:offset + limit]])

    @router.post("/{dataset_id}/preprocess", response_model=PreprocessResponse, status_code=201)
    def preprocess_dataset(dataset_id: str, body: PreprocessRequest) -> PreprocessResponse:
        session = get_session(dataset_id)
        with storage_lock, session.lock, artifact_errors():
            prepared = session.prepared.get(body.prepared_id)
            if prepared is None:
                raise HTTPException(404, "Prepared dataset not found for this dataset")
            if body.artifact_id is not None:
                artifact = get_artifact(session, artifact_adapter, body.prepared_id, body.artifact_id)
                check_input_budget(artifact, getattr(prepared, body.partition))
                if body.model_id is not None:
                    if model_store is None or model_runtime is None:
                        raise HTTPException(409, "Model service is not configured")
                    from presentation.apis.models.routes import model_errors
                    from infrastructure.adapters.preprocessing.phishing_detection.tokenizer_adapter import PhishingDetectionTokenizerPreprocessor
                    with model_errors(), model_store.borrow(body.model_id) as (model, directory):
                        if model.bundle.task != CyberTask.PHISHING_DETECTION:
                            raise ValueError("Selected model must be a phishing transformer")
                        tokenizer = (model_runtime.tokenizer(directory) if model.has_tokenizer
                                     else artifact_adapter.load_tokenizer(artifact))
                    selected_preprocessor = PhishingDetectionTokenizerPreprocessor(artifact, tokenizer)
                else:
                    selected_preprocessor = preprocessor_for(artifact_adapter, artifact)
            else:
                if body.model_id is not None:
                    raise ValueError("Select preprocessing artifacts when specifying model_id")
                selected_preprocessor = PhishingDetectionTextPreprocessor()
                if artifact_adapter is not None or selected_preprocessor is None:
                    raise HTTPException(409, "Create and select preprocessing artifacts first")
            transformed = PreprocessPhishingDetectionDataset(selected_preprocessor).execute(prepared, body.partition)
            transformed = replace(transformed, artifact_id=body.artifact_id, partition=body.partition, model_id=body.model_id)
            preprocessed_id = str(uuid4())
            session.preprocessed[preprocessed_id] = transformed
            return PreprocessResponse(dataset_id=dataset_id, prepared_id=body.prepared_id,
                                      preprocessed_id=preprocessed_id, artifact_id=body.artifact_id, partition=body.partition, model_id=body.model_id, sample_count=len(transformed.row_ids))

    @router.get("/{dataset_id}/preprocessed/{preprocessed_id}", response_model=RecordsResponse)
    def preprocessed_records(dataset_id: str, preprocessed_id: str,
                             offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=1000)) -> RecordsResponse:
        session = get_session(dataset_id)
        with storage_lock, session.lock:
            transformed = session.preprocessed.get(preprocessed_id)
            if transformed is None:
                raise HTTPException(404, "Preprocessed data not found for this dataset")
            stop = min(offset + limit, len(transformed.row_ids))
            records = [dict(row_id=transformed.row_ids[i], text=transformed.texts[i], label=transformed.labels[i],
                            candidate_labels=transformed.candidate_labels,
                            token_type_ids=[list(pair[:64]) for pair in transformed.token_type_ids[i]] if transformed.token_type_ids else [],
                            input_ids=[list(pair[:64]) for pair in transformed.input_ids[i]] if transformed.input_ids else [],
                            attention_mask=[list(pair[:64]) for pair in transformed.attention_mask[i]] if transformed.attention_mask else [],
                            token_length=len(transformed.input_ids[i][0]) if transformed.input_ids else 0)
                       for i in range(offset, stop)]
            return RecordsResponse(total=len(transformed.row_ids), offset=offset, limit=limit, records=records)

    @router.delete("/{dataset_id}", status_code=204)
    def unload_dataset(dataset_id: str) -> Response:
        session = get_session(dataset_id)
        with storage_lock, session.lock:
            if cleanup is not None: cleanup(dataset_id, session)
            sessions.pop(dataset_id, None)
        return Response(status_code=204)

    add_reset_routes(router, get_session, cleanup, storage_lock)
    add_download_routes(router, get_session, ExportPhishingDetectionDataset(PhishingDetectionZIPExporter()))
    add_artifact_routes(router, get_session, artifact_adapter, model_store, model_runtime, storage_lock, delete_artifact)
    return router
