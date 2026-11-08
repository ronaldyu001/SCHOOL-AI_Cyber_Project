/** Mirrors presentation/apis/datasets/schemas.py. Keep in step with the backend. */

export type Partition = 'train' | 'test' | 'eval';

export const PARTITIONS: readonly Partition[] = ['train', 'test', 'eval'];

export interface SplitRequest {
  seed: number;
  train_fraction: number;
  test_fraction: number;
  eval_fraction: number;
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
  partition: Partition;
  artifact_id: string | null;
  /** The model whose tokenizer produced this result; only phishing sets it. */
  model_id: string | null;
  sample_count: number;
}

export interface RecordsResponse {
  total: number;
  offset: number;
  limit: number;
  records: Record<string, unknown>[];
}

/* Model bundles. Mirrors presentation/apis/models/routes.py. */

/** One architecture per task: transformer/phishing, malconv/malware, tabm/network. */
export type ModelArchitecture = 'transformer' | 'malconv' | 'tabm';

/**
 * What the model's raw output means. The service owns this, not the upload, so
 * it is the same for every model of an architecture.
 */
export interface OutputContract {
  kind: string;
  columns?: string[];
  positive_label?: number;
  /** Label 0 and label 1 by name, e.g. `{"0": "benign", "1": "malware"}`. */
  prediction_labels: Record<string, string>;
}

export interface UploadedModel {
  model_id: string;
  task: string;
  architecture: ModelArchitecture;
  config: Record<string, unknown>;
  has_tokenizer: boolean;
  output_contract: OutputContract;
  /** Only the inspect route returns this, and only for transformers. */
  transformer_config?: Record<string, unknown>;
}

export interface ModelCapabilities {
  format: string;
  weights: string;
  architectures: ModelArchitecture[];
  transformer_families: string[];
  output_contracts: Record<string, OutputContract>;
  optional_tokenizer: string;
}

export interface PredictionResponse {
  model_id: string;
  row_ids: (string | number)[];
  /** Probability of label 1, one per row, in the preprocessed partition's order. */
  positive_probabilities: number[];
  predictions: number[];
  output_contract: OutputContract;
  /** Every prediction is saved, so it can be evaluated without the session. */
  result_id: string;
  task: string;
}

/* Saved results and analysis. Mirrors presentation/apis/results/. */

export interface ResultMetadata {
  schema_version: number;
  result_id: string;
  task: string;
  dataset_id: string;
  preprocessed_id: string;
  model_id: string;
  architecture: ModelArchitecture;
  has_tokenizer: boolean;
  source: Record<string, unknown>;
  artifact_id: string | null;
  partition: string;
  sample_count: number;
  created_at: string;
  output_contract: OutputContract;
  /** Network only; names the columns an attribution refers to. */
  numeric_features?: string[];
  categorical_features?: string[];
  /** Phishing only. */
  candidate_labels?: string[];
}

export interface ResultRows {
  row_ids: number[];
  true_labels: number[];
  positive_probabilities: number[];
  predictions: number[];
}

export interface ResultDetail {
  metadata: ResultMetadata;
  total: number;
  offset: number;
  limit: number;
  rows: ResultRows;
}

export interface EvaluationMetrics {
  log_loss: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  /** Null when the partition holds only one true class. */
  roc_auc: number | null;
  average_precision: number | null;
}

export interface ClassScore {
  precision: number;
  recall: number;
  'f1-score': number;
  support: number;
}

export interface Evaluation {
  sample_count: number;
  threshold: number;
  metrics: EvaluationMetrics;
  /** Per class plus the macro/weighted rows; `accuracy` is a bare number. */
  classification_report: Record<string, ClassScore | number>;
  confusion_matrix: { labels: string[]; true_axis: string; predicted_axis: string; values: number[][] };
  roc_curve: { false_positive_rate: number[]; true_positive_rate: number[]; thresholds: (number | null)[] } | null;
  precision_recall_curve: { precision: number[]; recall: number[]; thresholds: number[] } | null;
  warnings: string[];
}

export interface AnalysisParameters {
  explain: boolean;
  row_ids: number[] | null;
  sample_count: number;
  n_steps: number;
  internal_batch_size: number;
  n_repeats: number;
  seed: number;
  include_byte_attributions: boolean;
}

export interface AnalysisSummary {
  analysis_id: string;
  created_at: string;
  parameters: AnalysisParameters;
}

/** Attributions for one row. The fields present depend on the task. */
export interface ExplanationSample {
  row_id: number;
  convergence_delta: number;
  /** Network. */
  numeric_values?: number[];
  categorical_ids?: number[];
  attributions?: number[];
  prediction_value?: number;
  baseline_value?: number;
  /** Malware. */
  sha256?: string;
  input_length?: number;
  retained_byte_length?: number;
  logit?: number;
  malware_probability?: number;
  baseline_logit?: number;
  attribution_sum?: number;
  windows?: { start: number; end: number; attribution: number }[];
  regions?: { name: string; attribution: number }[];
  top_bytes?: { offset: number; attribution: number }[];
  byte_attributions?: number[];
  /** Phishing. */
  tokens?: string[];
  token_ids?: number[];
  margin?: number;
  baseline_margin?: number;
  phishing_probability?: number;
  retained_premise_tokens?: number;
}

export interface Explainability {
  method: string;
  target: string;
  baseline: string;
  samples: ExplanationSample[];
  feature_names?: string[];
  global_importance?: { features: string[]; mean_absolute_attribution: number[] };
  feature_permutation?: {
    available: boolean;
    features?: string[];
    feature_types?: string[];
    importance?: number[];
    std?: number[];
    repeats?: number;
    target?: string;
    reason?: string;
  } | null;
  global_token_importance?: {
    token: string;
    mean_attribution: number;
    mean_absolute_attribution: number;
    count: number;
  }[];
}

export interface Analysis {
  schema_version: number;
  task: string;
  result_id: string;
  analysis_id: string;
  created_at: string;
  parameters: AnalysisParameters;
  evaluation: Evaluation;
  /** Null unless the request asked to explain. */
  explainability: Explainability | null;
}

export interface StoredArtifact {
  artifact_id: string;
  valid: boolean;
  manifest?: PreprocessingArtifact['manifest'];
  task?: string;
  error?: string;
}

export interface PreprocessingArtifact {
  artifact_id: string;
  manifest: {
    schema_version: number;
    task: string;
    settings: Record<string, unknown>;
    provenance: { dataset_version: string; training_fingerprint: string; training_sample_count: number };
    files: Record<string, string>;
  };
}
