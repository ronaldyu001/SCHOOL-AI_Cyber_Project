"""Optional operation observer; synchronous calls remain valid without a job."""
from contextlib import contextmanager
from contextvars import ContextVar

class OperationCancelled(RuntimeError):
    pass

_observer = ContextVar('operation_observer', default=None)

def checkpoint():
    observer = _observer.get()
    if observer is not None: observer(None, None, None)

def report_progress(phase, completed=0, total=0):
    observer = _observer.get()
    if observer is not None: observer(phase, completed, total)

@contextmanager
def observe_operation(observer):
    token = _observer.set(observer)
    try: yield
    finally: _observer.reset(token)
