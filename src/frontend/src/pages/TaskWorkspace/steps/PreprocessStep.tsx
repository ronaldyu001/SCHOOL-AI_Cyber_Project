import { useBackgroundJob } from '../../../jobs/use-background-job';
import { JobProgress } from '../../../jobs/JobProgress';
import { useState } from 'react';
import { artifactDownloadUrl, createPreprocessingArtifact, inspectPreprocessingArtifact, startPreprocessing } from '../../../api/datasets';
import type { Partition, PreprocessResponse, PreprocessingArtifact, UploadedModel } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, NumberField, StatusNote, Summary } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { ArtifactFileBadge, ArtifactPanel } from '../ArtifactPanel';
import { StageDownload } from '../StageDownload';
import { useAction } from '../use-action';

interface PreprocessStepProps {
  onReset?: () => void;
  model: UploadedModel | null;
  task: TaskDescriptor;
  datasetId: string | null;
  preparedId: string | null;
  preprocessed: PreprocessResponse | null;
  onPreprocessed: (preprocessed: PreprocessResponse) => void;
}

export function PreprocessStep({ model, onReset, task, datasetId, preparedId, preprocessed, onPreprocessed }: PreprocessStepProps) {
  const [artifacts, setArtifacts] = useState<PreprocessingArtifact[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [partition, setPartition] = useState<Partition>('eval');
  const [maxLength, setMaxLength] = useState(task.slug === 'malware_detection' ? 1048576 : 1024);
  const selectedModel = task.slug === 'phishing_detection' ? model?.model_id : undefined;
  const artifact = artifacts.find((item) => item.artifact_id === selectedId);
  const create = useAction(async (dataset: string, prepared: string) => {
    const settings = task.slug === 'network_intrusion' ? {} : { max_length: maxLength };
    const result = await createPreprocessingArtifact(task.slug, dataset, prepared, settings, selectedModel);
    setArtifacts((current) => current.some((item) => item.artifact_id === result.artifact_id) ? current : [...current, result]);
    setSelectedId(result.artifact_id);
  });
  const inspect = useAction(async (dataset: string, id: string) => {
    const result = await inspectPreprocessingArtifact(task.slug, dataset, id);
    setArtifacts((current) => current.map((item) => item.artifact_id === id ? result : item));
  });
  const operation = useBackgroundJob<PreprocessResponse>(onPreprocessed);
  const action = useAction(async (dataset: string, prepared: string, id: string) => {
    operation.track(await startPreprocessing(task.slug, dataset, prepared, id, partition, selectedModel));
  });
  const busy = create.pending || inspect.pending || action.pending || operation.active;

  return (
    <StepCard onReset={onReset} step={6} title="Preprocess" description="Create reusable preprocessing artifacts, then transform a partition."
      state={preprocessed !== null ? 'done' : preparedId === null ? 'locked' : 'ready'} lockedHint="Prepare the partitions first.">
      {datasetId === null || preparedId === null ? null : (
        <>
          <p className="work__hint">{task.slug === 'network_intrusion'
            ? 'Fits median imputation, standard scaling, and category mappings on train only.'
            : task.slug === 'phishing_detection'
              ? 'Packages the selected tokenizer with fixed candidate labels and input settings.'
              : 'Packages byte encoding, padding, and truncation settings. No fitting is needed.'}</p>
          {task.slug === 'network_intrusion' ? null : (
            <NumberField id="artifact-length" label="Maximum input length"
              hint={task.slug === 'malware_detection' ? 'Bytes retained per file' : 'Tokens per candidate pair; the backend takes 16 to 1024'}
              value={maxLength} min={task.slug === 'malware_detection' ? 1 : 16}
              step={1} disabled={busy} onChange={setMaxLength} />
          )}
          {task.slug === 'phishing_detection' ? <p className="work__hint">{model === null
            ? 'Select a model above before preprocessing for inference. Downloads can still use the default tokenizer.'
            : `Tokenizing for model ${model.model_id.slice(0, 16)} using ${model.has_tokenizer ? 'its included tokenizer' : 'the service default tokenizer'}.`}</p> : null}
          <div className="work__row">
            <Button pending={create.pending} disabled={busy} onClick={() => void create.run(datasetId, preparedId)}>Create artifacts</Button>
          </div>
          {artifacts.length === 0 ? null : (
            <>
              <label className="field"><span className="field__label">Artifact version</span>
                <select className="field__input" value={selectedId} disabled={busy} onChange={(event) => setSelectedId(event.target.value)}>
                  {artifacts.map((item) => <option key={item.artifact_id} value={item.artifact_id}>{item.artifact_id.slice(0, 16)}</option>)}
                </select>
              </label>
              <div className="work__row">
                <Button pending={inspect.pending} disabled={busy} onClick={() => void inspect.run(datasetId, selectedId)}>Refresh from server</Button>
                {artifact === undefined ? null : <ArtifactFileBadge artifact={artifact} />}
              </div>
            </>
          )}
          {artifact === undefined ? null : (
            <ArtifactPanel
              artifact={artifact}
              downloadUrl={artifactDownloadUrl(task.slug, datasetId, artifact.artifact_id)}
            />
          )}
          <label className="field"><span className="field__label">Partition to transform</span>
            <select className="field__input" value={partition} disabled={busy} onChange={(event) => setPartition(event.target.value as Partition)}>
              <option value="train">Train</option><option value="test">Test</option><option value="eval">Eval</option>
            </select>
          </label>
          <div className="work__row"><Button variant="primary" pending={action.pending} disabled={busy || artifact === undefined}
            onClick={() => void action.run(datasetId, preparedId, selectedId)}>Preprocess {partition} partition</Button></div>
          <JobProgress job={operation.job} error={operation.error} onCancel={operation.cancel} />
          {[create.error, inspect.error, action.error].filter((error) => error !== null).map((error, index) => <StatusNote key={index} tone="danger">{error}</StatusNote>)}
          {preprocessed === null ? null : (
            <>
              <Summary items={[
                { label: 'Partition', value: preprocessed.partition, mono: true },
                { label: 'Samples', value: preprocessed.sample_count.toLocaleString() },
                { label: 'Artifact', value: preprocessed.artifact_id?.slice(0, 16) ?? 'External', mono: true },
                { label: 'Model', value: preprocessed.model_id?.slice(0, 16) ?? 'None', mono: true },
              ]} />
              {/* The partition is fixed by the result, so this export takes none. */}
              <StageDownload slug={task.slug} datasetId={datasetId} stage="preprocessed" resultId={preprocessed.preprocessed_id}
                label={`Download preprocessed ${preprocessed.partition} (.zip)`}
                contents="The full transformed arrays, untruncated, with the encoding metadata the records panel only previews." />
            </>
          )}
        </>
      )}
    </StepCard>
  );
}
