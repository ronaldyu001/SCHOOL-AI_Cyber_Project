from fastapi import APIRouter, HTTPException
from infrastructure.adapters.jobs import JobNotFound

def create_router(jobs):
    router = APIRouter(prefix='/jobs', tags=['background jobs'])
    @router.get('/{job_id}')
    def status(job_id: str):
        try: return jobs.status(job_id)
        except JobNotFound as error: raise HTTPException(404, str(error)) from error
    @router.get('/{job_id}/result')
    def result(job_id: str):
        try: return jobs.result(job_id)
        except JobNotFound as error: raise HTTPException(404, str(error)) from error
        except ValueError as error: raise HTTPException(409, str(error)) from error
    @router.post('/{job_id}/cancel', status_code=202)
    def cancel(job_id: str):
        try: return jobs.cancel_job(job_id)
        except JobNotFound as error: raise HTTPException(404, str(error)) from error
    return router
