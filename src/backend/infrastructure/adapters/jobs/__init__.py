"""Bounded background operation queue with independently readable progress."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, RLock
from uuid import uuid4
from application.ports.progress import OperationCancelled, observe_operation

TERMINAL = {'succeeded', 'failed', 'cancelled'}

def now(): return datetime.now(timezone.utc).isoformat()

class JobNotFound(LookupError): pass

@dataclass
class Job:
    info: dict
    key: tuple
    operation: object
    cancel: Event = field(default_factory=Event)

class JobRunner:
    def __init__(self):
        self.lock = RLock()
        self.entries = {}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='cyber-job')
        self.temporary = TemporaryDirectory(prefix='cyber-job-results-')
        self.root = Path(self.temporary.name)
        self.closed = False

    def submit(self, kind, references, key, operation):
        with self.lock:
            if self.closed: raise ValueError('Job service is stopping')
            for job in self.entries.values():
                if job.key == key and job.info['status'] not in TERMINAL:
                    return dict(job.info)
            if sum(j.info['status'] not in TERMINAL for j in self.entries.values()) >= 16:
                raise ValueError('The job queue is full; wait for a running job or cancel one')
            # Keep a bounded terminal history; large payloads are temporary disk files, not RAM copies.
            finished = [k for k,j in self.entries.items() if j.info['status'] in TERMINAL]
            for old in finished[:-99]:
                (self.root / (old+'.json')).unlink(missing_ok=True)
                del self.entries[old]
            job_id = uuid4().hex
            info = dict(job_id=job_id, kind=kind, status='queued', phase='queued', completed=0, total=0,
                        percent=0, created_at=now(), started_at=None, finished_at=None, error=None, **references)
            job = Job(info, key, operation)
            self.entries[job_id] = job
            self.executor.submit(self._run, job)
            return dict(info)

    def _run(self, job):
        def observe(phase, completed, total):
            if job.cancel.is_set(): raise OperationCancelled('Operation cancelled')
            if phase is not None:
                with self.lock:
                    fraction = completed/total if total else 0
                    percent = round(fraction*95, 1)
                    if phase == 'saving_results': percent = round(95+fraction*4, 1)
                    job.info.update(phase=phase, completed=completed, total=total, percent=percent)
        try:
            with self.lock:
                if job.cancel.is_set(): raise OperationCancelled('Operation cancelled')
                job.info.update(status='running', phase='starting', started_at=now())
                operation, job.operation = job.operation, None
            with observe_operation(observe):
                payload = operation()
            if hasattr(payload, 'model_dump'): payload = payload.model_dump(mode='json')
            path = self.root / (job.info['job_id']+'.json')
            path.write_text(json.dumps(payload, allow_nan=False))
            with self.lock:
                if job.info.get('invalidated'):
                    path.unlink(missing_ok=True)
                    raise OperationCancelled('Operation cancelled')
                summary = {k: payload[k] for k in ('result_id','analysis_id','preprocessed_id','task') if k in payload}
                job.info.update(status='succeeded', phase='completed', percent=100, result=summary)
        except OperationCancelled as error:
            with self.lock: job.info.update(status='cancelled', phase='cancelled', error=str(error))
        except Exception as error:
            with self.lock:
                job.info.update(status='failed', phase='failed', error=str(getattr(error, 'detail', error)))
        finally:
            with self.lock:
                job.operation = None
                job.info['finished_at'] = now()

    def status(self, job_id):
        with self.lock:
            if job_id not in self.entries: raise JobNotFound('Job not found; it may have expired or the API restarted')
            return dict(self.entries[job_id].info)

    def result(self, job_id):
        with self.lock:
            state = self.status(job_id)
            if state['status'] != 'succeeded': raise ValueError(state['error'] or 'Job has not completed')
            return json.loads((self.root/(job_id+'.json')).read_text())

    def cancel_job(self, job_id):
        with self.lock:
            self.status(job_id)
            job = self.entries[job_id]
            if job.info['status'] not in TERMINAL:
                job.cancel.set()
                if job.info['status'] == 'queued':
                    job.operation = None
                    job.info.update(status='cancelled', phase='cancelled', finished_at=now(), error='Operation cancelled')
                else: job.info['status'] = 'cancelling'
            return dict(job.info)

    def cancel_matching(self, **references):
        with self.lock:
            for job in self.entries.values():
                if all(job.info.get(k) == v for k,v in references.items()):
                    self.cancel_job(job.info['job_id'])

    def invalidate(self, **references):
        with self.lock:
            self.cancel_matching(**references)
            for job in self.entries.values():
                if all(job.info.get(k) == v for k,v in references.items()):
                    job.info['invalidated'] = True
                if all(job.info.get(k) == v for k,v in references.items()) and job.info['status'] == 'succeeded':
                    job.info.update(status='cancelled', phase='cancelled', error='The underlying dataset or result was released')
                    (self.root/(job.info['job_id']+'.json')).unlink(missing_ok=True)

    def close(self):
        with self.lock:
            self.closed = True
            self.cancel_matching()
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.temporary.cleanup()
