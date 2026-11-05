"""Dataset-scoped stage selection and attachment responses."""
from typing import Literal
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from starlette.background import BackgroundTask
from presentation.apis.datasets.errors import dataset_errors


def add_download_routes(router, get_session, use_case):
    @router.get("/{dataset_id}/download", response_class=StreamingResponse,
                responses={200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}}})
    def download_dataset(dataset_id: str,
                         stage: Literal["loaded", "cleaned", "splits", "prepared", "preprocessed"],
                         result_id: str | None = None,
                         partition: Literal["train", "test", "eval", "all"] | None = None):
        session = get_session(dataset_id)
        with session.lock, dataset_errors():
            if stage in ("loaded", "cleaned"):
                if result_id is not None:
                    raise ValueError("This stage does not accept result_id")
                dataset = getattr(session, stage)
                if dataset is None:
                    raise HTTPException(409, "Clean the dataset before downloading cleaned data")
            else:
                if not result_id:
                    raise ValueError("result_id is required for this stage")
                dataset = getattr(session, stage).get(result_id)
                if dataset is None:
                    raise HTTPException(404, "Stage result not found for this dataset")
            exported = use_case.execute(dataset, partition)
        def chunks():
            try:
                while chunk := exported.stream.read(64 * 1024):
                    yield chunk
            finally:
                exported.stream.close()
        return StreamingResponse(chunks(), media_type=exported.media_type,
                                 headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
                                 background=BackgroundTask(exported.stream.close))
