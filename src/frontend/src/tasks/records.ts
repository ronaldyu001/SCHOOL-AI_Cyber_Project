/**
 * Turns API records into table columns and cells.
 *
 * Both tasks return `row_id` and `label`; network records carry `numeric` and
 * `categorical` tuples, phishing records carry `text`. Tuples are expanded into
 * one named column per feature so the table stays readable.
 */
import type { TaskDescriptor } from './catalog';

export type CellKind = 'id' | 'number' | 'category' | 'text' | 'label';

export interface TableColumn {
  key: string;
  label: string;
  kind: CellKind;
}

export interface TableModel {
  columns: TableColumn[];
  rows: Record<string, unknown>[];
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

    if (key === 'row_id') {
      columns.push({ key, label: 'Row', kind: 'id' });
    } else if (key === 'label') {
      columns.push({ key, label: 'Label', kind: 'label' });
    } else if (key === 'text') {
      columns.push({ key, label: 'Email text', kind: 'text' });
    } else if (key === 'numeric' && Array.isArray(value)) {
      columns.push(...featureColumns('numeric', value, task.features?.numeric, 'number'));
    } else if (key === 'categorical' && Array.isArray(value)) {
      columns.push(...featureColumns('categorical', value, task.features?.categorical, 'category'));
    } else {
      columns.push({ key, label: key, kind: typeof value === 'number' ? 'number' : 'text' });
    }
  }

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
