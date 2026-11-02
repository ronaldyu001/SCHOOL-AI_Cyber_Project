/** Mirrors presentation/apis/datasets/schemas.py. Keep in step with the backend. */

export type Partition = 'train' | 'test' | 'eval';

export const PARTITIONS: readonly Partition[] = ['train', 'test', 'eval'];

export interface SplitRequest {
  seed: number;
  train_fraction: number;
  holdout_test_fraction: number;
}

export interface SourceResponse {
  dataset_id: string;
  task: string;
  filename: string;
  version: string;
  sample_count: number;
  columns: string[];
}

export interface CleanResponse {
  dataset_id: string;
  sample_count: number;
  removed_sample_count: number;
  schema_version: string;
}

export interface SplitResponse {
  dataset_id: string;
  split_id: string;
  seed: number;
  train_count: number;
  test_count: number;
  eval_count: number;
}

export interface PrepareResponse {
  dataset_id: string;
  split_id: string;
  prepared_id: string;
  train_count: number;
  test_count: number;
  eval_count: number;
}

export interface PreprocessResponse {
  dataset_id: string;
  prepared_id: string;
  preprocessed_id: string;
  partition: string;
  sample_count: number;
}

export interface RecordsResponse {
  total: number;
  offset: number;
  limit: number;
  records: Record<string, unknown>[];
}
