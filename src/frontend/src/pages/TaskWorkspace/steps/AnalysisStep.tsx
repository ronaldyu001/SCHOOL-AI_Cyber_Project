import { useBackgroundJob } from '../../../jobs/use-background-job';
import { JobProgress } from '../../../jobs/JobProgress';
/**
 * Evaluating and explaining the saved prediction.
 *
 * The result carries its own snapshot of the model and the exact preprocessed
 * inputs, so this step reads from `/results` rather than from the live session:
 * metrics cover the whole partition, explanations only the sampled rows.
 */
import { useEffect, useState } from 'react';
import type { TaskSlug } from '../../../api/datasets';
import {
  startAnalysis,
  deleteAnalysis,
  inspectAnalysis,
  listAnalyses,
  resultDownloadUrl,
} from '../../../api/results';
import type { Analysis, AnalysisSummary } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, DownloadLink, NumberField, StatusNote } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { AnalysisView } from '../analysis/AnalysisView';

const when = (iso: string) => {
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? iso : at.toLocaleString();
};

interface AnalysisStepProps {
  task: TaskDescriptor;
  /** The result the predict step saved, or null before anything is scored. */
  resultId: string | null;
}

export function AnalysisStep({ task, resultId }: AnalysisStepProps) {
  const slug: TaskSlug = task.slug;
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [explain, setExplain] = useState(false);
  const [sampleCount, setSampleCount] = useState(4);
  const [steps, setSteps] = useState(24);
  const [seed, setSeed] = useState(123);
  const [byteAttributions, setByteAttributions] = useState(false);
  const [busyAction, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (resultId === null) return;
    const controller = new AbortController();
    listAnalyses(slug, resultId, controller.signal)
      .then(setAnalyses)
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setError(caught instanceof Error ? caught.message : 'Unexpected error');
      });
    return () => controller.abort();
  }, [slug, resultId]);

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unexpected error');
    } finally {
      setBusy(null);
    }
  };

  const operation = useBackgroundJob<Analysis>(async (payload) => {
    setAnalysis(payload);
    if (resultId !== null) setAnalyses(await listAnalyses(slug, resultId));
    setNotice(payload.parameters.explain ? 'Evaluated the partition and attributed the sampled rows.' : 'Evaluated the partition.');
  });
  const busy = busyAction ?? (operation.active ? 'analysis' : null);
  const analyse = () => {
    if (resultId === null) return;
    void run('analysis', async () => {
      operation.track(await startAnalysis(slug, resultId, {
        explain, sample_count: sampleCount, n_steps: steps, seed, include_byte_attributions: byteAttributions,
      }));
    });
  };

  return (
    <StepCard
      step={8}
      title="Evaluate"
      description="Scores the saved result into metrics and curves, and optionally explains individual rows."
      state={analysis !== null ? 'done' : resultId === null ? 'locked' : 'ready'}
      lockedHint="Score a partition first."
    >
      {resultId === null ? null : (
        <>
          <p className="work__hint">
            Metrics always cover the whole partition. Explanations attribute a seeded,
            class-balanced sample and run on CPU, so keep the sample small; permutation importance
            needs several rows before it says anything.
          </p>

          <div className="work__analysis-form">
            <label className="work__check">
              <input
                type="checkbox"
                checked={explain}
                disabled={busy !== null}
                onChange={(event) => setExplain(event.target.checked)}
              />
              Explain sampled rows
            </label>
            {!explain ? null : (
              <>
                <NumberField id="analysis-samples" label="Rows to explain" hint="1 to 2000"
                  value={sampleCount} min={1} max={2000} step={1} disabled={busy !== null}
                  onChange={setSampleCount} />
                <NumberField id="analysis-steps" label="IG steps" hint="2 to 512"
                  value={steps} min={2} max={512} step={1} disabled={busy !== null} onChange={setSteps} />
                <NumberField id="analysis-seed" label="Seed" hint="Picks the balanced sample"
                  value={seed} min={0} max={4294967295} step={1} disabled={busy !== null} onChange={setSeed} />
                {task.slug !== 'malware_detection' ? null : (
                  <label className="work__check">
                    <input
                      type="checkbox"
                      checked={byteAttributions}
                      disabled={busy !== null}
                      onChange={(event) => setByteAttributions(event.target.checked)}
                    />
                    Include every byte
                  </label>
                )}
              </>
            )}
          </div>

          <div className="work__row">
            <Button variant="primary" pending={busy === 'analysis'} disabled={busy !== null} onClick={analyse}>
              Run analysis
            </Button>
            <DownloadLink disabled={busy !== null} href={resultDownloadUrl(slug, resultId)}>
              Download result (.zip)
            </DownloadLink>
          </div>

          <JobProgress job={operation.job} error={operation.error} onCancel={operation.cancel} />
          {error === null ? null : <StatusNote tone="danger">{error}</StatusNote>}
          {notice === null ? null : <StatusNote tone="ok">{notice}</StatusNote>}

          {analyses.length === 0 ? null : (
            <ul className="work__analyses">
              {analyses.map((item) => (
                <li className="work__analysis-row" key={item.analysis_id}>
                  <span className="work__analysis-id">
                    <code className="mono">{item.analysis_id.slice(0, 12)}…</code>
                    <span className="work__hint">
                      {`${item.parameters.explain ? 'with explanations' : 'evaluation only'} · ${when(item.created_at)}`}
                    </span>
                  </span>
                  <span className="work__row">
                    <Button
                      pending={busy === item.analysis_id}
                      disabled={busy !== null}
                      onClick={() =>
                        void run(item.analysis_id, async () => {
                          setAnalysis(await inspectAnalysis(slug, resultId, item.analysis_id));
                        })
                      }
                    >
                      {analysis?.analysis_id === item.analysis_id ? 'Shown' : 'Open'}
                    </Button>
                    <Button
                      variant="danger"
                      disabled={busy !== null}
                      onClick={() =>
                        void run(item.analysis_id, async () => {
                          await deleteAnalysis(slug, resultId, item.analysis_id);
                          if (analysis?.analysis_id === item.analysis_id) setAnalysis(null);
                          setAnalyses(await listAnalyses(slug, resultId));
                        })
                      }
                    >
                      Delete
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
          )}

          {analysis === null ? null : <AnalysisView analysis={analysis} />}
        </>
      )}
    </StepCard>
  );
}
