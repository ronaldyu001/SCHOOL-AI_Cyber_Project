/** One function per dataset endpoint exposed by the backend routers. */
import { BASE_URL, request } from './client';
import type {
  CleanResponse,
  PreprocessingArtifact,
  Partition,
  PrepareResponse,
  PreprocessResponse,
  RecordsResponse,
  SourceResponse,
  SplitRequest,
  SplitResponse,
} from './types';

/** Router prefix segment, e.g. `network_intrusion`. */
export type TaskSlug = 'network_intrusion' | 'phishing_detection' | 'malware_detection';

/** `token_offset` / `token_limit`: a window into one preprocessed byte sequence. */
export interface TokenWindow {
  offset: number;
  limit: number;
}

const root = (slug: TaskSlug) => `/datasets/${slug}`;

export const loadDataset = (slug: TaskSlug) =>
  request<SourceResponse>(`${root(slug)}/load`, { method: 'POST' });

export const cleanDataset = (slug: TaskSlug, datasetId: string) =>
  request<CleanResponse>(`${root(slug)}/${datasetId}/clean`, { method: 'POST' });

export const createSplit = (slug: TaskSlug, datasetId: string, body: SplitRequest) =>
  request<SplitResponse>(`${root(slug)}/${datasetId}/splits`, { method: 'POST', body });

export const prepareDataset = (slug: TaskSlug, datasetId: string, splitId: string) =>
  request<PrepareResponse>(`${root(slug)}/${datasetId}/prepare`, {
    method: 'POST',
    body: { split_id: splitId },
  });

export const preprocessDataset = (slug: TaskSlug, datasetId: string, preparedId: string, artifactId?: string, partition: Partition = 'eval') =>
  request<PreprocessResponse>(`${root(slug)}/${datasetId}/preprocess`, {
    method: 'POST',
    body: { prepared_id: preparedId, artifact_id: artifactId, partition },
  });

export const fetchPreparedRecords = (
  slug: TaskSlug,
  datasetId: string,
  preparedId: string,
  partition: Partition,
  offset: number,
  limit: number,
  signal?: AbortSignal,
) =>
  request<RecordsResponse>(
    `${root(slug)}/${datasetId}/prepared/${preparedId}/${partition}?offset=${offset}&limit=${limit}`,
    { signal },
  );

export const fetchPreprocessedRecords = (
  slug: TaskSlug,
  datasetId: string,
  preprocessedId: string,
  offset: number,
  limit: number,
  signal?: AbortSignal,
  /** Slice of each byte-token sequence to return, for tasks that produce one. */
  tokens?: TokenWindow,
) => {
  const window =
    tokens === undefined ? '' : `&token_offset=${tokens.offset}&token_limit=${tokens.limit}`;
  return request<RecordsResponse>(
    `${root(slug)}/${datasetId}/preprocessed/${preprocessedId}?offset=${offset}&limit=${limit}${window}`,
    { signal },
  );
};

export const unloadDataset = (slug: TaskSlug, datasetId: string) =>
  request<void>(`${root(slug)}/${datasetId}`, { method: 'DELETE' });

/**
 * The same unload, for the paths where nothing can act on a failure: leaving
 * the workspace, or a closing tab. `keepalive` is what lets it outlive the
 * document during `pagehide`, and a session that is already gone answers 404,
 * which is the outcome this wanted anyway.
 */
export const releaseDataset = async (slug: TaskSlug, datasetId: string) => {
  try {
    await request<void>(`${root(slug)}/${datasetId}`, { method: 'DELETE', keepalive: true });
  } catch {
    // Nothing left to report to.
  }
};

export const createPreprocessingArtifact = (slug: TaskSlug, datasetId: string, preparedId: string, settings: Record<string, unknown> = {}) =>
  request<PreprocessingArtifact>(`${root(slug)}/${datasetId}/artifacts`, {
    method: 'POST', body: { prepared_id: preparedId, settings },
  });

export const inspectPreprocessingArtifact = (slug: TaskSlug, datasetId: string, artifactId: string) =>
  request<PreprocessingArtifact>(`${root(slug)}/${datasetId}/artifacts/${artifactId}`);

export const artifactDownloadUrl = (slug: TaskSlug, datasetId: string, artifactId: string) =>
  `${BASE_URL}${root(slug)}/${datasetId}/artifacts/${artifactId}/download`;

/**
 * Stages the export route serves. `loaded` and `cleaned` are single results and
 * reject a `result_id`; the other three are keyed by the id their step returned.
 */
export type DownloadStage = 'loaded' | 'cleaned' | 'splits' | 'prepared' | 'preprocessed';

/** Only `prepared` holds all three partitions at once, so only it takes this. */
export type DownloadPartition = Partition | 'all';

/**
 * Builds the URL for a stage export. The browser fetches it directly rather
 * than going through `request`, so a bundle streams to disk instead of being
 * buffered in memory.
 */
export const datasetDownloadUrl = (
  slug: TaskSlug,
  datasetId: string,
  stage: DownloadStage,
  resultId?: string,
  partition?: DownloadPartition,
) => {
  const query = new URLSearchParams({ stage });
  if (resultId !== undefined) query.set('result_id', resultId);
  if (partition !== undefined) query.set('partition', partition);
  return `${BASE_URL}${root(slug)}/${datasetId}/download?${query.toString()}`;
};

/** Reset this stage and all dependent results, retaining the loaded dataset. */
export type ResetStage = 'cleaned' | 'splits' | 'prepared' | 'preprocessed';
export const resetDatasetStage = (slug: TaskSlug, datasetId: string, stage: ResetStage) =>
  request<void>(`${root(slug)}/${datasetId}/stages/${stage}`, { method: 'DELETE' });
