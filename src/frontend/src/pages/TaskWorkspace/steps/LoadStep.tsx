import { useEffect, useRef } from 'react';
import { loadDataset, releaseDataset } from '../../../api/datasets';
import type { SourceResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, StatusNote, Summary } from '../../../components/ui';
import { recordNote, type TaskDescriptor } from '../../../tasks/catalog';
import { StageDownload } from '../StageDownload';
import { useAction } from '../use-action';

interface LoadStepProps {
  task: TaskDescriptor;
  source: SourceResponse | null;
  /** The current session has been dropped; nothing is loaded yet. */
  onReleased: () => void | Promise<void>;
  onLoaded: (source: SourceResponse) => void;
}

export function LoadStep({ task, source, onReleased, onLoaded }: LoadStepProps) {
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const load = useAction(async () => {
    if (source !== null) {
      // Released before the new load rather than after it, so the two datasets
      // are never resident at once; a malware source is large enough that the
      // peak is the whole point. The local results go with it, so a reload that
      // then fails leaves nothing loaded instead of a dead dataset id on screen.
      await releaseDataset(task.slug, source.dataset_id);
      await onReleased();
    }
    const next = await loadDataset(task.slug);
    if (!mounted.current) {
      // Leaving mid-load still opens the session, since the request finishes
      // server-side either way, and the workspace released whatever it knew
      // about on the way out. Nothing would ever reach this one otherwise.
      void releaseDataset(task.slug, next.dataset_id);
      return;
    }
    onLoaded(next);
  });

  const digest = source === null ? '' : source.version.replace('sha256:', '');

  return (
    <StepCard
      step={1}
      title="Load dataset"
      description={`Reads the bundled ${task.datasetFile} and opens a dataset session.`}
      state={source === null ? 'ready' : 'done'}
    >
      <div className="work__row">
        <Button variant="primary" pending={load.pending} onClick={() => void load.run()}>
          {source === null ? 'Load dataset' : 'Reload dataset'}
        </Button>
      </div>

      {load.error === null ? null : <StatusNote tone="danger">{load.error}</StatusNote>}

      {source === null ? null : (
        <>
          <Summary
            items={[
              { label: 'Samples', value: source.sample_count.toLocaleString() },
              { label: 'Columns', value: source.columns.length },
              { label: 'File', value: source.filename, mono: true },
              { label: 'Task', value: source.task, mono: true },
            ]}
          />
          <p className="work__digest">
            sha256 <code title={digest}>{digest.slice(0, 16)}…</code>
          </p>
          <details className="work__columns">
            <summary>Source columns</summary>
            <ul>
              {source.columns.map((column) => (
                <li className="mono" key={column}>
                  {column}
                </li>
              ))}
            </ul>
          </details>
          <StageDownload
            slug={task.slug}
            datasetId={source.dataset_id}
            stage="loaded"
            label="Download loaded data (.zip)"
            contents={`Every row as read from the source file, with the columns and digest in the manifest.${recordNote(task)}`}
          />
        </>
      )}
    </StepCard>
  );
}
