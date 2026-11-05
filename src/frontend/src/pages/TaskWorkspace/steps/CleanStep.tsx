import { cleanDataset } from '../../../api/datasets';
import type { CleanResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, StatusNote, Summary } from '../../../components/ui';
import { recordNote, type TaskDescriptor } from '../../../tasks/catalog';
import { StageDownload } from '../StageDownload';
import { useAction } from '../use-action';

interface CleanStepProps {
  onReset?: () => void;
  task: TaskDescriptor;
  datasetId: string | null;
  cleaned: CleanResponse | null;
  onCleaned: (cleaned: CleanResponse) => void;
}

export function CleanStep({ onReset, task, datasetId, cleaned, onCleaned }: CleanStepProps) {
  const clean = useAction(async (id: string) => {
    onCleaned(await cleanDataset(task.slug, id));
  });

  return (
    <StepCard onReset={onReset}
      step={2}
      title="Clean"
      description="Drops unusable rows and pins the schema version."
      state={cleaned !== null ? 'done' : datasetId === null ? 'locked' : 'ready'}
      lockedHint="Load the dataset first."
    >
      {datasetId === null ? null : (
        <>
          <div className="work__row">
            <Button variant="primary" pending={clean.pending} onClick={() => void clean.run(datasetId)}>
              Clean dataset
            </Button>
          </div>

          {clean.error === null ? null : <StatusNote tone="danger">{clean.error}</StatusNote>}

          {cleaned === null ? null : (
            <>
              <Summary
                items={[
                  { label: 'Kept', value: cleaned.sample_count.toLocaleString() },
                  { label: 'Removed', value: cleaned.removed_sample_count.toLocaleString() },
                  { label: 'Schema', value: cleaned.schema_version, mono: true },
                ]}
              />
              <StageDownload
                slug={task.slug}
                datasetId={datasetId}
                stage="cleaned"
                label="Download cleaned data (.zip)"
                contents={`The rows that survived cleaning, under the pinned schema version.${recordNote(task)}`}
              />
            </>
          )}
        </>
      )}
    </StepCard>
  );
}
