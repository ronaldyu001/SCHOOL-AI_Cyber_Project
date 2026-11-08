"""Reset a dataset stage and its dependent in-memory results."""
from typing import Literal
from fastapi import Response

ResetStage = Literal["cleaned", "splits", "prepared", "preprocessed"]
STAGES = ("cleaned", "splits", "prepared", "preprocessed")


def reset_stage(session, stage: ResetStage) -> None:
    if stage not in STAGES:
        raise ValueError("Unknown reset stage")
    for downstream in STAGES[STAGES.index(stage):]:
        if downstream == "cleaned":
            session.cleaned = None
        else:
            getattr(session, downstream).clear()
        if downstream == "prepared":
            session.artifact_bindings.clear()


def add_reset_routes(router, get_session, cleanup=None, storage_lock=None, cancel_jobs=None):
    from threading import RLock
    storage_lock = storage_lock or RLock()
    @router.delete("/{dataset_id}/stages/{stage}", status_code=204)
    def reset_dataset_stage(dataset_id: str, stage: ResetStage) -> Response:
        session = get_session(dataset_id)
        if cancel_jobs is not None: cancel_jobs(dataset_id)
        with storage_lock, session.lock:
            if cleanup is not None: cleanup(dataset_id, session, stage)
            reset_stage(session, stage)
        return Response(status_code=204)
