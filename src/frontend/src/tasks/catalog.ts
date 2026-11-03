/** The cybersecurity tasks offered on the landing page. */
import type { TaskSlug } from '../api/datasets';

export interface TaskDescriptor {
  slug: TaskSlug;
  name: string;
  summary: string;
  /** Bundled source file the backend loads from `.data/<slug>/`. */
  datasetFile: string;
  /** Display names for label 0 and label 1. */
  labels: [string, string];
  /** Whether the backend exposes a router for this task. */
  available: boolean;
  /** Fixed feature order used to name the columns of a network record. */
  features?: { numeric: readonly string[]; categorical: readonly string[] };
  /** Preprocessed records are padded byte sequences the explorer pages through. */
  byteTokens?: boolean;
  /** Shown on the preprocess step when the backend cannot run it yet. */
  preprocessNote?: string;
  unavailableNote?: string;
}

/**
 * Feature order is part of the `ton_iot_binary_v1` checkpoint contract and
 * matches domain/entities/datasets/network_intrusion/schema.py.
 */
const NETWORK_NUMERIC = [
  'src_port', 'dst_port', 'duration', 'src_bytes', 'dst_bytes', 'missed_bytes',
  'src_pkts', 'src_ip_bytes', 'dst_pkts', 'dst_ip_bytes', 'dns_qclass',
  'dns_qtype', 'dns_rcode', 'http_request_body_len', 'http_response_body_len',
  'http_status_code',
] as const;

const NETWORK_CATEGORICAL = ['src_ip', 'dst_ip', 'proto', 'service', 'conn_state'] as const;

export const TASKS: readonly TaskDescriptor[] = [
  {
    slug: 'network_intrusion',
    name: 'Network Intrusion',
    summary:
      'Classify ToN_IoT network flows as normal traffic or an attack, using 16 numeric and 5 categorical flow features.',
    datasetFile: 'train_test_network.csv',
    labels: ['Normal', 'Attack'],
    available: true,
    features: { numeric: NETWORK_NUMERIC, categorical: NETWORK_CATEGORICAL },
    preprocessNote:
      'Preprocessing needs the fitted preprocessor from the trained TabM checkpoint. The backend returns 409 until that is wired into create_app().',
  },
  {
    slug: 'phishing_detection',
    name: 'Phishing Detection',
    summary:
      'Classify email text as legitimate or phishing/spam over a combined email corpus, with text normalisation applied at preprocess time.',
    datasetFile: 'phishing_email.csv',
    labels: ['Legitimate', 'Phishing'],
    available: true,
  },
  {
    slug: 'malware_detection',
    name: 'Malware Detection',
    summary:
      'Classify executables as benign or malicious from their raw bytes, read out of a ZIP archive whose filenames are the SHA-256 of each sample.',
    datasetFile: 'MalwareDetectionDataset.zip',
    labels: ['Benign', 'Malicious'],
    available: true,
    byteTokens: true,
    preprocessNote:
      'Preprocessing needs the byte preprocessor matching the trained checkpoint. The backend returns 409 until that is wired into create_app().',
  },
];

export const findTask = (slug: string): TaskDescriptor | undefined =>
  TASKS.find((task) => task.slug === slug);
