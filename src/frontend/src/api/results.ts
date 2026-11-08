/**
 * Saved predictions, their analyses, and the stored preprocessing artifacts.
 *
 * Both outlive the dataset session that produced them: a result carries its own
 * snapshot of the model and inputs, so it can be evaluated and explained after
 * the dataset is unloaded or the API restarts.
 */
import { BASE_URL, request } from './client';
import type { TaskSlug } from './datasets';
import type {
  Analysis,
  AnalysisParameters,
  AnalysisSummary,
  ResultDetail,
  ResultMetadata,
  StoredArtifact,
} from './types';

const results = (task: TaskSlug) => `/results/${task}`;

export const listResults = (task: TaskSlug, datasetId?: string, signal?: AbortSignal) =>
  request<ResultMetadata[]>(
    datasetId === undefined ? results(task) : `${results(task)}?dataset_id=${encodeURIComponent(datasetId)}`,
    { signal },
  );

export const inspectResult = (task: TaskSlug, resultId: string, offset: number, limit: number, signal?: AbortSignal) =>
  request<ResultDetail>(`${results(task)}/${resultId}?offset=${offset}&limit=${limit}`, { signal });

export const deleteResult = (task: TaskSlug, resultId: string) =>
  request<void>(`${results(task)}/${resultId}`, { method: 'DELETE' });

export const clearResults = (task: TaskSlug) =>
  request<void>(results(task), { method: 'DELETE' });

/** Metadata, prediction rows and saved analyses; not the model or input snapshots. */
export const resultDownloadUrl = (task: TaskSlug, resultId: string) =>
  `${BASE_URL}${results(task)}/${resultId}/download`;

/**
 * Runs synchronously on CPU. Evaluation always covers the whole partition;
 * `explain` additionally attributes the selected rows, which is the slow part.
 */
export const createAnalysis = (task: TaskSlug, resultId: string, body: Partial<AnalysisParameters>) =>
  request<Analysis>(`${results(task)}/${resultId}/analysis`, { method: 'POST', body });

export const listAnalyses = (task: TaskSlug, resultId: string, signal?: AbortSignal) =>
  request<AnalysisSummary[]>(`${results(task)}/${resultId}/analysis`, { signal });

export const inspectAnalysis = (task: TaskSlug, resultId: string, analysisId: string) =>
  request<Analysis>(`${results(task)}/${resultId}/analysis/${analysisId}`);

export const deleteAnalysis = (task: TaskSlug, resultId: string, analysisId: string) =>
  request<void>(`${results(task)}/${resultId}/analysis/${analysisId}`, { method: 'DELETE' });

const artifacts = (task: TaskSlug) => `/artifacts/${task}`;

export const listStoredArtifacts = (task: TaskSlug, signal?: AbortSignal) =>
  request<StoredArtifact[]>(artifacts(task), { signal });

/** Also deletes every saved result that used this artifact. */
export const deleteStoredArtifact = (task: TaskSlug, artifactId: string) =>
  request<void>(`${artifacts(task)}/${artifactId}`, { method: 'DELETE' });

export const clearStoredArtifacts = (task: TaskSlug) =>
  request<void>(artifacts(task), { method: 'DELETE' });

export const storedArtifactDownloadUrl = (task: TaskSlug, artifactId: string) =>
  `${BASE_URL}${artifacts(task)}/${artifactId}/download`;

export const startAnalysis = (task: TaskSlug, resultId: string, body: Partial<AnalysisParameters>) =>
  request<import('./jobs').JobStatus>(`${results(task)}/${resultId}/analysis/jobs`, { method: 'POST', body });
