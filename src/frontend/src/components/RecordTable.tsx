/** Scrollable table of dataset records, with long text collapsed per row. */
import { useState } from 'react';
import type { TaskDescriptor } from '../tasks/catalog';
import { buildTable, formatCell, formatTokens } from '../tasks/records';
import { Badge } from './ui';
import './RecordTable.css';

const TEXT_PREVIEW_LENGTH = 180;

interface RecordTableProps {
  task: TaskDescriptor;
  records: Record<string, unknown>[];
  /** Absolute index of the first record, so the row counter matches the API offset. */
  offset: number;
}

export function RecordTable({ task, records, offset }: RecordTableProps) {
  const [expanded, setExpanded] = useState<ReadonlySet<number>>(new Set());
  const { columns, rows } = buildTable(task, records);

  if (columns.length === 0) {
    return <p className="records__empty">No records in this range.</p>;
  }

  const toggle = (index: number) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div className="records">
      <table className="records__table">
        <caption className="sr-only">
          {`Records ${offset + 1} to ${offset + rows.length} for the ${task.name} dataset`}
        </caption>
        <thead>
          <tr>
            <th scope="col" className="records__index">
              #
            </th>
            {columns.map((column) => (
              <th scope="col" key={column.key} className={`records__cell--${column.kind}`}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.row_id ?? index)}>
              <td className="records__index mono">{offset + index + 1}</td>
              {columns.map((column) => {
                const value = row[column.key];

                if (column.kind === 'label') {
                  const numeric = Number(value);
                  const name = task.labels[numeric === 1 ? 1 : 0];
                  return (
                    <td key={column.key} className="records__cell--label">
                      <Badge tone={numeric === 1 ? 'danger' : 'ok'}>{`${name} (${formatCell(value)})`}</Badge>
                    </td>
                  );
                }

                if (column.kind === 'text') {
                  const text = formatCell(value);
                  const isLong = text.length > TEXT_PREVIEW_LENGTH;
                  const isOpen = expanded.has(index);
                  return (
                    <td key={column.key} className="records__cell--text">
                      <span className="records__text">{isLong && !isOpen ? `${text.slice(0, TEXT_PREVIEW_LENGTH)}…` : text}</span>
                      {isLong ? (
                        <button type="button" className="records__toggle" onClick={() => toggle(index)}>
                          {isOpen ? 'Show less' : 'Show more'}
                        </button>
                      ) : null}
                    </td>
                  );
                }

                if (column.kind === 'hash') {
                  const hash = formatCell(value);
                  return (
                    <td key={column.key} className="records__cell--hash mono" title={hash}>
                      {hash.length > 16 ? `${hash.slice(0, 16)}…` : hash}
                    </td>
                  );
                }

                if (column.kind === 'bytes') {
                  return (
                    <td key={column.key} className="records__cell--bytes">
                      <span className="records__bytes mono">{formatTokens(value, row)}</span>
                    </td>
                  );
                }

                return (
                  <td key={column.key} className={`records__cell--${column.kind} mono`}>
                    {formatCell(value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
