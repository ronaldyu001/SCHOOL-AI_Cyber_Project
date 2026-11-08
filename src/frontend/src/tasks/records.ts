/**
 * Turns API records into table columns and cells.
 *
 * Every task returns `row_id` and `label`. Network records carry `numeric` and
 * `categorical` tuples, phishing records carry `text`, malware records carry a
 * hash, archive path and — once preprocessed — a window of `byte_tokens`.
 * Tuples are expanded into one named column per feature so the table stays
 * readable.
 */
import type { TaskDescriptor } from './catalog';

export type CellKind = 'id' | 'number' | 'category' | 'text' | 'label' | 'hash' | 'bytes';

export interface TableColumn {
  key: string;
  label: string;
  kind: CellKind;
}

export interface TableModel {
  columns: TableColumn[];
  rows: Record<string, unknown>[];
}

/** Record keys that mean the same thing wherever the backend returns them. */
const NAMED: Record<string, { label: string; kind: CellKind }> = {
  row_id: { label: 'Row', kind: 'id' },
  label: { label: 'Label', kind: 'label' },
  text: { label: 'Email text', kind: 'text' },
  sha256: { label: 'SHA-256', kind: 'hash' },
  relative_path: { label: 'Archive path', kind: 'text' },
  size_bytes: { label: 'Size (bytes)', kind: 'number' },
  length: { label: 'Bytes kept', kind: 'number' },
  byte_tokens: { label: 'Byte tokens', kind: 'bytes' },
  // Tokenized phishing output. Each is one list per candidate pair, so they
  // read as long rows; naming them at least says which is which.
  input_ids: { label: 'Input IDs', kind: 'text' },
  attention_mask: { label: 'Attention mask', kind: 'text' },
  token_type_ids: { label: 'Token type IDs', kind: 'text' },
  candidate_labels: { label: 'Candidates', kind: 'text' },
  token_length: { label: 'Tokens', kind: 'number' },
};

/**
 * Byte-token encoding fields. They hold the same value on every row of a page,
 * so the explorer states them once rather than repeating them as columns.
 */
const ENCODING = new Set(['max_length', 'byte_offset', 'padding_token', 'token_offset']);

export interface TokenEncoding {
  maxLength: number;
  byteOffset: number;
  paddingToken: number;
  tokenOffset: number;
}

/** Reads the byte-token encoding off a page of records, or null if it has none. */
export function readEncoding(records: Record<string, unknown>[]): TokenEncoding | null {
  const first = records[0];
  if (first === undefined || !Array.isArray(first.byte_tokens)) return null;
  const read = (key: string, fallback: number) =>
    typeof first[key] === 'number' ? (first[key] as number) : fallback;
  return {
    maxLength: read('max_length', 0),
    byteOffset: read('byte_offset', 0),
    paddingToken: read('padding_token', 256),
    tokenOffset: read('token_offset', 0),
  };
}

function featureColumns(
  key: 'numeric' | 'categorical',
  values: unknown[],
  names: readonly string[] | undefined,
  kind: CellKind,
): TableColumn[] {
  return values.map((_, index) => ({
    key: `${key}.${index}`,
    label: names?.[index] ?? `${key}[${index}]`,
    kind,
  }));
}

export function buildTable(task: TaskDescriptor, records: Record<string, unknown>[]): TableModel {
  const first = records[0];
  if (first === undefined) return { columns: [], rows: [] };

  const columns: TableColumn[] = [];

  for (const key of Object.keys(first)) {
    const value = first[key];
    const named = NAMED[key];

    if (ENCODING.has(key)) {
      continue;
    } else if (named !== undefined) {
      columns.push({ key, ...named });
    } else if (key === 'numeric' && Array.isArray(value)) {
      columns.push(...featureColumns('numeric', value, task.features?.numeric, 'number'));
    } else if (key === 'categorical' && Array.isArray(value)) {
      columns.push(...featureColumns('categorical', value, task.features?.categorical, 'category'));
    } else {
      columns.push({ key, label: key, kind: typeof value === 'number' ? 'number' : 'text' });
    }
  }

  // Encoding fields stay on the row even though they have no column: the byte
  // cell reads them to tell a padded token from a real zero byte.
  const rows = records.map((record) => {
    const row: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(record)) {
      if ((key === 'numeric' || key === 'categorical') && Array.isArray(value)) {
        value.forEach((item, index) => {
          row[`${key}.${index}`] = item;
        });
      } else {
        row[key] = value;
      }
    }
    return row;
  });

  return { columns, rows };
}

/** Keeps wide float columns from pushing the table out of view. */
export function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return String(value);
    return Number(value.toPrecision(6)).toString();
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  const text = String(value);
  return text.trim() === '' ? '—' : text;
}

/**
 * Byte tokens as hex pairs, undoing the checkpoint's byte offset so the values
 * read as the file's own bytes. Padding shows as `··` so a truncated sample
 * stays distinguishable from a run of zero bytes.
 */
export function formatTokens(value: unknown, row: Record<string, unknown>): string {
  if (!Array.isArray(value)) return formatCell(value);
  if (value.length === 0) return '—';
  const offset = typeof row.byte_offset === 'number' ? row.byte_offset : 0;
  const padding = row.padding_token;
  return value
    .map((token) =>
      token === padding ? '··' : (Number(token) - offset).toString(16).padStart(2, '0'),
    )
    .join(' ');
}
