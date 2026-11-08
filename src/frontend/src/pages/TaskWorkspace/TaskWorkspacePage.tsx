/** Dataset pipeline for one task: load, clean, split, prepare, preprocess, browse. */
import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { resetDatasetStage, type ResetStage, unloadDataset } from '../../api/datasets';
import type {
  CleanResponse,
  PrepareResponse,
  PreprocessResponse,
  SourceResponse,
  SplitResponse,
  UploadedModel,
} from '../../api/types';
import { Button, StatusNote } from '../../components/ui';
import { findTask, type TaskDescriptor } from '../../tasks/catalog';
import { NotFoundPage } from '../NotFoundPage';
import { RecordExplorer, type RecordView } from './RecordExplorer';
import { CleanStep } from './steps/CleanStep';
import { useModelRelease } from './use-model-release';
import { AnalysisStep } from './steps/AnalysisStep';
import { ModelStep } from './steps/ModelStep';
import { LoadStep } from './steps/LoadStep';
import { PredictStep } from './steps/PredictStep';
import { PrepareStep } from './steps/PrepareStep';
import { PreprocessStep } from './steps/PreprocessStep';
import { SplitStep } from './steps/SplitStep';
import { useAction } from './use-action';
import { ActionScopeContext, useActionScope } from './action-scope';
import { useSessionRelease } from './use-session-release';
import './TaskWorkspacePage.css';

export function TaskWorkspaceRoute() {
  const { slug = '' } = useParams();
  const task = findTask(slug);

  if (task === undefined) return <NotFoundPage message={`No task named "${slug}".`} />;
  if (!task.available) {
    return <NotFoundPage message={`${task.name} is not available yet. ${task.unavailableNote ?? ''}`} />;
  }
  // Remount on task change so no pipeline state leaks between tasks.
  return <TaskWorkspaceScope key={task.slug} task={task} />;
}

function TaskWorkspaceScope({ task }: { task: TaskDescriptor }) {
  const scope = useActionScope();
  return <ActionScopeContext value={scope}><TaskWorkspace task={task} busy={scope.busy} /></ActionScopeContext>;
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

function TaskWorkspace({ task, busy }: { task: TaskDescriptor; busy: boolean }) {
  const modelRelease = useModelRelease();
  const [model, setModel] = useState<UploadedModel | null>(null);
  const selectedModel = useRef<UploadedModel | null>(null);
  const [pipeline, setPipeline] = useState<Pipeline>(EMPTY);
  const [revisions, setRevisions] = useState({ cleaned: 0, splits: 0, prepared: 0, preprocessed: 0 });
  const [view, setView] = useState<RecordView>('train');
  const [confirmUnload, setConfirmUnload] = useState(false);
  // Set once this dataset has saved a prediction. Unloading would delete those
  // results, so from then on the dataset is only released on purpose.
  const [savedResults, setSavedResults] = useState(false);
  // The result the predict step saved, which the evaluate step then analyses.
  const [resultId, setResultId] = useState<string | null>(null);
  const { source, cleaned, split, prepared, preprocessed } = pipeline;

  // Leaving the workspace has to delete the session, not just drop the local
  // state: the backend keeps it until asked otherwise.
  useSessionRelease(task.slug, source?.dataset_id ?? null, savedResults);

  /** Takes up a dataset, or none, discarding everything the last one produced. */
  const adopt = (next: SourceResponse | null) => {
    setPipeline(next === null ? EMPTY : { ...EMPTY, source: next });
    setConfirmUnload(false);
    setSavedResults(false);
    setResultId(null);
    setView('train');
  };

  const selectModel = async (next: UploadedModel | null, owned = false) => {
    if (next !== null && owned) modelRelease.track(next.model_id);
    const previous = selectedModel.current;
    if (previous?.model_id === next?.model_id) return;
    if (previous !== null) await modelRelease.release(previous.model_id);
    selectedModel.current = next;
    setModel(next);
    setPipeline((current) => ({ ...current, preprocessed: null }));
    setView('train');
  };

  const releaseWorkspaceModels = async () => {
    adopt(null);
    await modelRelease.releaseAll();
    selectedModel.current = null;
    setModel(null);
  };

  const unload = useAction(async (datasetId: string) => {
    await unloadDataset(task.slug, datasetId);
    await releaseWorkspaceModels();
  });

  const reset = useAction(async (stage: ResetStage) => {
    if (source === null) return;
    await resetDatasetStage(task.slug, source.dataset_id, stage);
    const stages: ResetStage[] = ['cleaned', 'splits', 'prepared', 'preprocessed'];
    const cleared = stages.slice(stages.indexOf(stage));
    setPipeline((current) => ({
      ...current,
      ...(cleared.includes('cleaned') ? { cleaned: null } : {}),
      ...(cleared.includes('splits') ? { split: null } : {}),
      ...(cleared.includes('prepared') ? { prepared: null } : {}),
      preprocessed: null,
    }));
    setRevisions((current) => {
      const next = { ...current };
      for (const item of cleared) next[item] += 1;
      return next;
    });
    setView('train');
    setConfirmUnload(false);
    setSavedResults(false);
    setResultId(null);
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
            <span className="work__session-note">
              {savedResults
                ? 'Kept while you have saved predictions from it. Unloading or resetting a stage deletes them.'
                : 'Held in the API\u2019s memory until you unload it, reload the dataset, or leave this page.'}
            </span>
          </div>
          <div className="work__row">
            {confirmUnload ? (
              <>
                <Button
                  variant="danger"
                  disabled={busy}
                  pending={unload.pending}
                  onClick={() => void unload.run(source.dataset_id)}
                >
                  Confirm unload
                </Button>
                <Button disabled={busy} onClick={() => setConfirmUnload(false)}>
                  Cancel
                </Button>
              </>
            ) : (
              <Button disabled={busy} variant="danger" onClick={() => setConfirmUnload(true)}>
                Unload dataset
              </Button>
            )}
          </div>
        </div>
      )}

      {unload.error === null ? null : <StatusNote tone="danger">{unload.error}</StatusNote>}

      {reset.error === null ? null : <StatusNote tone="danger">{reset.error}</StatusNote>}
      <fieldset className="work__controls" disabled={busy} aria-busy={busy}>
        <ol className="work__pipeline">
          <LoadStep
            task={task}
            source={source}
            onReleased={releaseWorkspaceModels}
            onLoaded={adopt}
          />
          <CleanStep
            key={`${source?.dataset_id}:cleaned:${revisions.cleaned}`}
            onReset={cleaned !== null ? () => void reset.run('cleaned') : undefined}
            task={task}
            datasetId={source?.dataset_id ?? null}
            cleaned={cleaned}
            onCleaned={(next) => setPipeline((current) => ({ ...EMPTY, source: current.source, cleaned: next }))}
          />
          <SplitStep
            key={`${source?.dataset_id}:splits:${revisions.splits}`}
            onReset={split !== null ? () => void reset.run('splits') : undefined}
            task={task}
            datasetId={source?.dataset_id ?? null}
            cleaned={cleaned !== null}
            split={split}
            onSplit={(next) =>
              setPipeline((current) => ({ ...current, split: next, prepared: null, preprocessed: null }))
            }
          />
          <PrepareStep
            key={`${source?.dataset_id}:prepared:${revisions.prepared}`}
            onReset={prepared !== null ? () => void reset.run('prepared') : undefined}
            task={task}
            datasetId={source?.dataset_id ?? null}
            splitId={split?.split_id ?? null}
            prepared={prepared}
            onPrepared={(next) => {
              setPipeline((current) => ({ ...current, prepared: next, preprocessed: null }));
              setView('train');
            }}
          />
          <ModelStep key={source?.dataset_id ?? "no-dataset"} task={task} datasetId={source?.dataset_id ?? null} model={model} onSelect={selectModel} />
          <PreprocessStep
            model={model}
            key={`${source?.dataset_id ?? "none"}:${prepared?.prepared_id ?? "none"}:${revisions.preprocessed}:${model?.model_id ?? "default"}`}
            onReset={prepared !== null ? () => void reset.run('preprocessed') : undefined}
            task={task}
            datasetId={source?.dataset_id ?? null}
            preparedId={prepared?.prepared_id ?? null}
            preprocessed={preprocessed}
            onPreprocessed={(next) => {
              setPipeline((current) => ({ ...current, preprocessed: next }));
              setView('preprocessed');
            }}
          />
          <PredictStep
            model={model}
            key={`${source?.dataset_id ?? 'none'}:predict:${preprocessed?.preprocessed_id ?? 'none'}:${model?.model_id ?? 'none'}`}
            task={task}
            datasetId={source?.dataset_id ?? null}
            preprocessed={preprocessed}
            onSaved={(saved) => {
              setSavedResults(true);
              setResultId(saved);
            }}
          />
          <AnalysisStep
            key={`${source?.dataset_id ?? 'none'}:evaluate:${resultId ?? 'none'}`}
            task={task}
            resultId={resultId}
          />
        </ol>
      </fieldset>

      <section className="work__panel">
        <h2>Records</h2>
        <p className="work__panel-lede">
          Page through the prepared partitions, or the preprocessed partition output once it exists.
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
