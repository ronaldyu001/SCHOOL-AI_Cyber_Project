/** One function per dataset endpoint exposed by the backend routers. */
import { request } from './client';
import type {
  CleanResponse,
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

export const preprocessDataset = (slug: TaskSlug, datasetId: string, preparedId: string) =>
  request<PreprocessResponse>(`${root(slug)}/${datasetId}/preprocess`, {
    method: 'POST',
    body: { prepared_id: preparedId },
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
