/** Paged viewer over prepared partitions and preprocessed output. */
import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { fetchPreparedRecords, fetchPreprocessedRecords } from '../../api/datasets';
import type { Partition, RecordsResponse } from '../../api/types';
import { PARTITIONS } from '../../api/types';
import { RecordTable } from '../../components/RecordTable';
import { Button, StatusNote } from '../../components/ui';
import type { TaskDescriptor } from '../../tasks/catalog';
import './RecordExplorer.css';

export type RecordView = Partition | 'preprocessed';

const PAGE_SIZES = [10, 25, 50, 100] as const;

/** Outcome of one request, tagged with the request it answers. */
interface Result {
  key: string;
  response: RecordsResponse | null;
  error: string | null;
}

interface RecordExplorerProps {
  task: TaskDescriptor;
  datasetId: string;
  preparedId: string;
  preprocessedId: string | null;
  view: RecordView;
  onViewChange: (view: RecordView) => void;
}

export function RecordExplorer({
  task,
  datasetId,
  preparedId,
  preprocessedId,
  view,
  onViewChange,
}: RecordExplorerProps) {
  const [limit, setLimit] = useState<number>(25);
  const [result, setResult] = useState<Result | null>(null);

  // Fall back to a prepared partition if preprocessed output was invalidated.
  const activeView: RecordView = view === 'preprocessed' && preprocessedId === null ? 'train' : view;
  const sourceId = activeView === 'preprocessed' ? preprocessedId : preparedId;

  // Deriving the page from a cursor keyed on the view avoids a reset effect
  // (and the extra fetch it would cause) when the view or page size changes.
  const cursorKey = `${activeView}:${sourceId ?? ''}:${limit}`;
  const [cursor, setCursor] = useState({ key: cursorKey, page: 0 });
  const page = cursor.key === cursorKey ? cursor.page : 0;
  const offset = page * limit;

  // Loading is derived, not stored: anything but an answer to the current
  // request means a request is still in flight.
  const requestKey = `${cursorKey}:${offset}`;
  const current = result?.key === requestKey ? result : null;
  const loading = current === null;

  useEffect(() => {
    if (sourceId === null) return;
    const controller = new AbortController();
    let cancelled = false;

    const pending =
      activeView === 'preprocessed'
        ? fetchPreprocessedRecords(task.slug, datasetId, sourceId, offset, limit, controller.signal)
        : fetchPreparedRecords(task.slug, datasetId, sourceId, activeView, offset, limit, controller.signal);

    pending
      .then((response) => {
        if (!cancelled) setResult({ key: requestKey, response, error: null });
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        if (caught instanceof DOMException && caught.name === 'AbortError') return;
        setResult({
          key: requestKey,
          response: null,
          error: caught instanceof ApiError ? caught.message : 'Could not fetch records',
        });
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [task.slug, datasetId, sourceId, activeView, offset, limit, requestKey]);

  const total = current?.response?.total ?? 0;
  const records = current?.response?.records ?? [];
  const lastPage = total === 0 ? 0 : Math.ceil(total / limit) - 1;
  const goTo = (next: number) => setCursor({ key: cursorKey, page: next });

  return (
    <div className="explorer">
      <div className="explorer__controls">
        <div className="explorer__views" role="group" aria-label="Record set">
          {PARTITIONS.map((partition) => (
            <button
              key={partition}
              type="button"
              className="explorer__view"
              aria-pressed={activeView === partition}
              onClick={() => onViewChange(partition)}
            >
              {partition}
            </button>
          ))}
          <button
            type="button"
            className="explorer__view"
            aria-pressed={activeView === 'preprocessed'}
            disabled={preprocessedId === null}
            title={preprocessedId === null ? 'Run the preprocess step first' : undefined}
            onClick={() => onViewChange('preprocessed')}
          >
            preprocessed
          </button>
        </div>

        <div className="explorer__size">
          <label htmlFor="page-size">Rows</label>
          <select
            id="page-size"
            className="explorer__select"
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          >
            {PAGE_SIZES.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
      </div>

      {current?.error == null ? null : <StatusNote tone="danger">{current.error}</StatusNote>}

      <p className="explorer__count" role="status">
        {loading
          ? 'Loading records…'
          : total === 0
            ? 'No records available.'
            : `Showing ${offset + 1}–${offset + records.length} of ${total.toLocaleString()}`}
      </p>

      {loading || records.length === 0 ? null : (
        <RecordTable task={task} records={records} offset={offset} />
      )}

      <div className="explorer__pager">
        <Button onClick={() => goTo(page - 1)} disabled={page === 0 || loading}>
          Previous
        </Button>
        <span className="explorer__page">
          Page {page + 1} of {lastPage + 1}
        </span>
        <Button onClick={() => goTo(page + 1)} disabled={page >= lastPage || loading}>
          Next
        </Button>
      </div>
    </div>
  );
}
