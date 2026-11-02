/** Dataset pipeline for one task: load, clean, split, prepare, preprocess, browse. */
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { unloadDataset } from '../../api/datasets';
import type {
  CleanResponse,
  PrepareResponse,
  PreprocessResponse,
  SourceResponse,
  SplitResponse,
} from '../../api/types';
import { Button, StatusNote } from '../../components/ui';
import { findTask, type TaskDescriptor } from '../../tasks/catalog';
import { NotFoundPage } from '../NotFoundPage';
import { RecordExplorer, type RecordView } from './RecordExplorer';
import { CleanStep } from './steps/CleanStep';
import { LoadStep } from './steps/LoadStep';
import { PrepareStep } from './steps/PrepareStep';
import { PreprocessStep } from './steps/PreprocessStep';
import { SplitStep } from './steps/SplitStep';
import { useAction } from './use-action';
import './TaskWorkspacePage.css';

export function TaskWorkspaceRoute() {
  const { slug = '' } = useParams();
  const task = findTask(slug);

  if (task === undefined) return <NotFoundPage message={`No task named "${slug}".`} />;
  if (!task.available) {
    return <NotFoundPage message={`${task.name} is not available yet. ${task.unavailableNote ?? ''}`} />;
  }
  // Remount on task change so no pipeline state leaks between tasks.
  return <TaskWorkspace key={task.slug} task={task} />;
}

/** Pipeline results. Each stage invalidates the ones after it. */
interface Pipeline {
  source: SourceResponse | null;
  cleaned: CleanResponse | null;
  split: SplitResponse | null;
  prepared: PrepareResponse | null;
  preprocessed: PreprocessResponse | null;
}

const EMPTY: Pipeline = {
  source: null,
  cleaned: null,
  split: null,
  prepared: null,
  preprocessed: null,
};

function TaskWorkspace({ task }: { task: TaskDescriptor }) {
  const [pipeline, setPipeline] = useState<Pipeline>(EMPTY);
  const [view, setView] = useState<RecordView>('train');
  const [confirmUnload, setConfirmUnload] = useState(false);
  const { source, cleaned, split, prepared, preprocessed } = pipeline;

  const unload = useAction(async (datasetId: string) => {
    await unloadDataset(task.slug, datasetId);
    setPipeline(EMPTY);
    setConfirmUnload(false);
    setView('train');
  });

  return (
    <section>
      <header className="work__header">
        <Link className="work__back" to="/">
          ← All tasks
        </Link>
        <h1>{task.name}</h1>
        <p className="work__summary">{task.summary}</p>
      </header>

      {source === null ? null : (
        <div className="work__session">
          <div className="work__session-info">
            <span className="work__session-label">Active dataset</span>
            <code className="work__session-id">{source.dataset_id}</code>
          </div>
          <div className="work__row">
            {confirmUnload ? (
              <>
                <Button
                  variant="danger"
                  pending={unload.pending}
                  onClick={() => void unload.run(source.dataset_id)}
                >
                  Confirm unload
                </Button>
                <Button disabled={unload.pending} onClick={() => setConfirmUnload(false)}>
                  Cancel
                </Button>
              </>
            ) : (
              <Button variant="danger" onClick={() => setConfirmUnload(true)}>
                Unload dataset
              </Button>
            )}
          </div>
        </div>
      )}

      {unload.error === null ? null : <StatusNote tone="danger">{unload.error}</StatusNote>}

      <ol className="work__pipeline">
        <LoadStep
          task={task}
          source={source}
          onLoaded={(next) => setPipeline({ ...EMPTY, source: next })}
        />
        <CleanStep
          task={task}
          datasetId={source?.dataset_id ?? null}
          cleaned={cleaned}
          onCleaned={(next) => setPipeline((current) => ({ ...EMPTY, source: current.source, cleaned: next }))}
        />
        <SplitStep
          task={task}
          datasetId={source?.dataset_id ?? null}
          cleaned={cleaned !== null}
          split={split}
          onSplit={(next) =>
            setPipeline((current) => ({ ...current, split: next, prepared: null, preprocessed: null }))
          }
        />
        <PrepareStep
          task={task}
          datasetId={source?.dataset_id ?? null}
          splitId={split?.split_id ?? null}
          prepared={prepared}
          onPrepared={(next) => {
            setPipeline((current) => ({ ...current, prepared: next, preprocessed: null }));
            setView('train');
          }}
        />
        <PreprocessStep
          task={task}
          datasetId={source?.dataset_id ?? null}
          preparedId={prepared?.prepared_id ?? null}
          preprocessed={preprocessed}
          onPreprocessed={(next) => {
            setPipeline((current) => ({ ...current, preprocessed: next }));
            setView('preprocessed');
          }}
        />
      </ol>

      <section className="work__panel">
        <h2>Records</h2>
        <p className="work__panel-lede">
          Page through the prepared partitions, or the preprocessed eval output once it exists.
        </p>
        {source === null || prepared === null ? (
          <p className="work__hint">Complete the prepare step to browse records.</p>
        ) : (
          <RecordExplorer
            task={task}
            datasetId={source.dataset_id}
            preparedId={prepared.prepared_id}
            preprocessedId={preprocessed?.preprocessed_id ?? null}
            view={view}
            onViewChange={setView}
          />
        )}
      </section>
    </section>
  );
}
