/**
 * One function per endpoint of the model router.
 *
 * Models are registered for the whole application rather than for a dataset
 * session. The task pipeline manages registrations it creates; the model library
 * also supports registrations shared across workspaces.
 */
import { BASE_URL, request } from './client';
import type { TaskSlug } from './datasets';
import type { ModelCapabilities, PredictionResponse, UploadedModel } from './types';

const ROOT = '/models';

export const fetchModelCapabilities = (signal?: AbortSignal) =>
  request<ModelCapabilities>(`${ROOT}/capabilities`, { signal });

export const listModels = (signal?: AbortSignal) => request<UploadedModel[]>(ROOT, { signal });

/** Returns the model with `transformer_config` filled in, where it has one. */
export const inspectModel = (modelId: string) => request<UploadedModel>(`${ROOT}/${modelId}`);

/**
 * Uploads the bundle as a raw ZIP body. The route wants the archive itself
 * under `application/zip`, and the browser streams a `File` rather than
 * holding it in memory, which matters at the route's 16 GiB ceiling.
 */
export const uploadModel = (file: File) =>
  request<UploadedModel>(`${ROOT}/upload`, {
    method: 'POST',
    body: file,
    contentType: 'application/zip',
  });

export const deleteModel = (modelId: string, keepalive = false) =>
  request<void>(`${ROOT}/${modelId}`, { method: 'DELETE', keepalive });

/** Streamed by the browser, like the dataset and artifact exports. */
export const modelDownloadUrl = (modelId: string) => `${BASE_URL}${ROOT}/${modelId}/download`;

export const predictWithModel = (modelId: string, datasetId: string, preprocessedId: string) =>
  request<PredictionResponse>(`${ROOT}/${modelId}/predict`, {
    method: 'POST',
    body: { dataset_id: datasetId, preprocessed_id: preprocessedId },
  });

/** One packaged notebook baseline, whether or not its bundle is installed. */
export interface BaselineModel {
  task: TaskSlug;
  architecture: string;
  name: string;
  available: boolean;
  reason?: string;
}
export const listBaselines = (signal?: AbortSignal) => request<BaselineModel[]>(`${ROOT}/baselines`, { signal });

/**
 * Registers this task's baseline through the ordinary import path. The first
 * call reads and validates the bundle; a later one reuses the registration and
 * says so, so nothing large is read twice.
 */
export const loadBaseline = (task: TaskSlug) =>
  request<UploadedModel & { reused: boolean; baseline_task: TaskSlug }>(`${ROOT}/baselines/${task}/load`, { method: 'POST' });

export const startPrediction = (modelId: string, datasetId: string, preprocessedId: string) =>
  request<import('./jobs').JobStatus>(`${ROOT}/${modelId}/predict/jobs`, { method: 'POST', body: { dataset_id: datasetId, preprocessed_id: preprocessedId } });
