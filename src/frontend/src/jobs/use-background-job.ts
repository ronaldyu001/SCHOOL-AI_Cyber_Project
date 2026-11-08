/** Poll lightweight job status, retry transient disconnects, and cancel abandoned work. */
import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';
import { cancelJob, inspectJob, readJobResult, type JobStatus } from '../api/jobs';

const terminal = (job: JobStatus) => ['succeeded', 'failed', 'cancelled'].includes(job.status);

export function useBackgroundJob<T>(onComplete: (payload: T) => void | Promise<void>) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(onComplete);
  const current = useRef<JobStatus | null>(null);
  const mounted = useRef(true);
  useEffect(() => { latest.current = onComplete; }, [onComplete]);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const jobId = job?.job_id;
  useEffect(() => {
    if (jobId === undefined) return;
    const controller = new AbortController();
    const { signal } = controller;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const wait = () => new Promise<void>((resolve) => {
      const finish = () => { if (timer) clearTimeout(timer); signal.removeEventListener('abort', finish); resolve(); };
      signal.addEventListener('abort', finish, { once: true });
      timer = setTimeout(finish, 1000);
    });
    const poll = async () => {
      while (!signal.aborted) {
        try {
          const status = await inspectJob(jobId, signal);
          if (signal.aborted) return;
          current.current = status;
          setJob(status);
          if (status.status === 'failed' || status.status === 'cancelled') {
            setError(status.error ?? 'Operation stopped.');
            return;
          }
          if (status.status === 'succeeded') {
            const payload = await readJobResult<T>(jobId, signal);
            if (signal.aborted) return;
            setError(null);
            try { await latest.current(payload); }
            catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not display completed result'); }
            return;
          }
          setError(null);
        } catch (caught) {
          if (signal.aborted) return;
          if (caught instanceof ApiError && caught.status === 404) {
            setError('This job is no longer available. The API may have restarted; run the operation again.');
            const previous = current.current;
            if (previous) { current.current = { ...previous, status: 'failed' }; setJob(current.current); }
            return;
          }
          setError('Connection interrupted. Retrying job status…');
        }
        await wait();
      }
    };
    void poll();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
      const previous = current.current;
      if (previous?.job_id === jobId && !terminal(previous)) void cancelJob(jobId, true).catch(() => undefined);
    };
  }, [jobId]);
  const track = (status: JobStatus) => {
    if (!mounted.current) { void cancelJob(status.job_id, true).catch(() => undefined); return; }
    current.current = status;
    setError(null);
    setJob(status);
  };
  const cancel = async () => {
    if (!current.current || terminal(current.current)) return;
    try {
      const status = await cancelJob(current.current.job_id);
      current.current = status;
      if (mounted.current) setJob(status);
    } catch (caught) { if (mounted.current) setError(caught instanceof Error ? caught.message : 'Could not cancel job'); }
  };
  return { job, error, active: job !== null && !terminal(job), track, cancel };
}
