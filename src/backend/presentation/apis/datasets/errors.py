"""Translate expected dataset failures consistently."""
from contextlib import contextmanager
from collections.abc import Iterator
from fastapi import HTTPException

@contextmanager
def dataset_errors() -> Iterator[None]:
    try:
        yield
    except FileNotFoundError as error:
        raise HTTPException(404, "Bundled dataset file not found") from error
    except (ValueError, UnicodeError) as error:
        raise HTTPException(422, str(error)) from error
    except OSError as error:
        raise HTTPException(503, "Dataset file could not be read") from error
