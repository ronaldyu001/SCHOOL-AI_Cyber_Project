/**
 * Choosing what will score the partition.
 *
 * The packaged notebook baseline is the default; uploading a bundle is the
 * alternative. `onSelect` is told whether this step registered the model, so
 * the workspace releases only what it created and leaves a reused baseline or
 * someone else's upload in place.
 */
import { useEffect, useRef, useState } from 'react';
import {
  type BaselineModel,
  inspectModel,
  listBaselines,
  loadBaseline,
  modelDownloadUrl,
  uploadModel,
} from '../../../api/models';
import type { UploadedModel } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Badge, Button, DownloadLink, StatusNote } from '../../../components/ui';
import { useModels } from '../../../models/use-models';
import type { TaskDescriptor } from '../../../tasks/catalog';
import '../analysis/Analysis.css';

/** `{"0": "benign", "1": "malware"}` reads as "0 benign · 1 malware". */
const labelsOf = (labels: Record<string, string>) =>
  Object.entries(labels)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([value, name]) => `${value} ${name}`)
    .join(' · ');

interface ModelStepProps {
  task: TaskDescriptor;
  datasetId: string | null;
  model: UploadedModel | null;
  /** `owned` marks a registration this step made, which the workspace releases. */
  onSelect: (model: UploadedModel | null, owned?: boolean) => void | Promise<void>;
}

export function ModelStep({ task, datasetId, model, onSelect }: ModelStepProps) {
  const { models, reload } = useModels();
  const [baselines, setBaselines] = useState<BaselineModel[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [details, setDetails] = useState<UploadedModel | null>(null);
  const picker = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    listBaselines(controller.signal)
      .then(setBaselines)
      .catch(() => {
        // Without a catalog the upload path still works, so this is not an error.
        setBaselines([]);
      });
    return () => controller.abort();
  }, []);

  const taskModels = models.filter((item) => item.task === task.slug);
  const baseline = baselines?.find((item) => item.task === task.slug);

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

  const useBaseline = () =>
    void run('baseline', async () => {
      const loaded = await loadBaseline(task.slug);
      // Borrowed, not ours: the backend packages this bundle and memoizes its
      // registration, so releasing it on the way out would only force the next
      // session to read it again — 1.6 GB of it, for phishing.
      await onSelect(loaded, false);
      setNotice(
        loaded.reused
          ? 'The baseline was already registered, so it was reused.'
          : `Registered the ${loaded.architecture} baseline.`,
      );
      setDetails(null);
      reload();
    });

  const upload = () => {
    if (file === null) return;
    void run('upload', async () => {
      const uploaded = await uploadModel(file);
      await onSelect(uploaded, true);
      setNotice(`Registered your ${uploaded.architecture} bundle.`);
      setFile(null);
      if (picker.current !== null) picker.current.value = '';
      setDetails(null);
      reload();
    });
  };

  const choose = (modelId: string) => {
    const next = taskModels.find((item) => item.model_id === modelId) ?? null;
    void run('select', async () => {
      await onSelect(next, false);
      setDetails(null);
      reload();
    });
  };

  return (
    <StepCard
      step={5}
      title="Model"
      description="Score with the packaged notebook baseline, or upload your own bundle."
      state={model !== null ? 'done' : datasetId === null ? 'locked' : 'ready'}
      lockedHint="Load a dataset first."
    >
      {datasetId === null ? null : (
        <>
          <p className="work__hint">
            {baseline === undefined
              ? 'Checking for a packaged baseline…'
              : baseline.available
                ? `${baseline.name} ships with the backend and is the default for this task. Upload a bundle only to score with your own.`
                : `No baseline is installed for this task${baseline.reason === undefined ? '' : `: ${baseline.reason}`}. Upload a bundle to score.`}
          </p>

          {taskModels.length === 0 ? null : (
            <label className="field">
              <span className="field__label">Registered model</span>
              <select
                className="field__input"
                value={model?.model_id ?? ''}
                disabled={busy !== null}
                onChange={(event) => choose(event.target.value)}
              >
                <option value="">None selected</option>
                {taskModels.map((item) => (
                  <option key={item.model_id} value={item.model_id}>
                    {item.architecture} · {item.model_id.slice(0, 16)}
                    {item.has_tokenizer ? ' · own tokenizer' : ''}
                  </option>
                ))}
              </select>
            </label>
          )}

          <div className="work__row">
            {baseline?.available !== true ? null : (
              <Button
                variant={model === null ? 'primary' : 'secondary'}
                pending={busy === 'baseline'}
                disabled={busy !== null}
                onClick={useBaseline}
              >
                Use baseline
              </Button>
            )}
            {model === null ? null : (
              <>
                <Button
                  pending={busy === 'details'}
                  disabled={busy !== null}
                  onClick={() => {
                    if (details !== null) {
                      setDetails(null);
                      return;
                    }
                    void run('details', async () => {
                      setDetails(await inspectModel(model.model_id));
                    });
                  }}
                >
                  {details === null ? 'Configuration' : 'Hide configuration'}
                </Button>
                <DownloadLink disabled={busy !== null} href={modelDownloadUrl(model.model_id)}>
                  Download bundle (.zip)
                </DownloadLink>
              </>
            )}
          </div>

          <details className="work__upload">
            <summary>Upload your own bundle</summary>
            <div className="work__upload-body">
              <p className="work__hint">
                A data-only ZIP holding <code>manifest.json</code> and safetensors weights. It is
                validated by loading it, so an unusable bundle is refused here rather than at
                prediction time.
              </p>
              <div className="work__row">
                <input
                  className="work__file"
                  ref={picker}
                  type="file"
                  accept=".zip,application/zip"
                  disabled={busy !== null}
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
                <Button
                  pending={busy === 'upload'}
                  disabled={busy !== null || file === null}
                  onClick={upload}
                >
                  Upload model
                </Button>
              </div>
            </div>
          </details>

          {error === null ? null : <StatusNote tone="danger">{error}</StatusNote>}
          {notice === null ? null : <StatusNote tone="ok">{notice}</StatusNote>}

          {model === null ? null : (
            <>
              <div className="work__row">
                <Badge tone="accent">{model.architecture}</Badge>
                {model.has_tokenizer ? <Badge tone="ok">Tokenizer</Badge> : null}
                <span className="work__hint">
                  Predicts {labelsOf(model.output_contract.prediction_labels)}
                  {task.slug === 'phishing_detection' && model.has_tokenizer
                    ? '. Its tokenizer replaces the default one when the artifact is built.'
                    : ''}
                </span>
              </div>
              {details === null ? null : (
                <>
                  <dl className="facts">
                    {Object.entries(details.config)
                      .filter(([, value]) => value === null || typeof value !== 'object')
                      .map(([key, value]) => (
                        <div className="facts__row" key={key}>
                          <dt>{key}</dt>
                          <dd className="mono">{String(value)}</dd>
                        </div>
                      ))}
                  </dl>
                  {Object.entries(details.config)
                    .filter(([, value]) => value !== null && typeof value === 'object')
                    .map(([key, value]) => (
                      <details className="analysis__raw" key={key}>
                        <summary>{key}</summary>
                        <pre>{JSON.stringify(value, null, 2)}</pre>
                      </details>
                    ))}
                  {details.transformer_config === undefined ? null : (
                    <details className="analysis__raw">
                      <summary>config.json</summary>
                      <pre>{JSON.stringify(details.transformer_config, null, 2)}</pre>
                    </details>
                  )}
                </>
              )}
            </>
          )}
        </>
      )}
    </StepCard>
  );
}
