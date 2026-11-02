import { loadDataset } from '../../../api/datasets';
import type { SourceResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, StatusNote, Summary } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { useAction } from '../use-action';

interface LoadStepProps {
  task: TaskDescriptor;
  source: SourceResponse | null;
  onLoaded: (source: SourceResponse) => void;
}

export function LoadStep({ task, source, onLoaded }: LoadStepProps) {
  const load = useAction(async () => {
    onLoaded(await loadDataset(task.slug));
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
        </>
      )}
    </StepCard>
  );
}
