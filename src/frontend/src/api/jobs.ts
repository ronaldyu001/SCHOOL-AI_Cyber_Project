import { request } from './client';

export interface JobStatus {
  job_id: string;
  kind: string;
  status: 'queued' | 'running' | 'cancelling' | 'succeeded' | 'failed' | 'cancelled';
  phase: string;
  completed: number;
  total: number;
  percent: number;
  error: string | null;
  result?: Record<string, string>;
}
export const inspectJob = (id: string, signal?: AbortSignal) => request<JobStatus>(`/jobs/${id}`, { signal });
export const readJobResult = <T,>(id: string, signal?: AbortSignal) => request<T>(`/jobs/${id}/result`, { signal });
export const cancelJob = (id: string, keepalive = false) => request<JobStatus>(`/jobs/${id}/cancel`, { method: 'POST', keepalive });
