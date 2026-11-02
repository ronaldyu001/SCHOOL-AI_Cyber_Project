import { preprocessDataset } from '../../../api/datasets';
import type { PreprocessResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, StatusNote, Summary } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { useAction } from '../use-action';

interface PreprocessStepProps {
  task: TaskDescriptor;
  datasetId: string | null;
  preparedId: string | null;
  preprocessed: PreprocessResponse | null;
  onPreprocessed: (preprocessed: PreprocessResponse) => void;
}

export function PreprocessStep({
  task,
  datasetId,
  preparedId,
  preprocessed,
  onPreprocessed,
}: PreprocessStepProps) {
  const action = useAction(async (id: string, prepared: string) => {
    onPreprocessed(await preprocessDataset(task.slug, id, prepared));
  });

  // A 409 means the backend has no fitted preprocessor wired up, not a failure
  // the user can fix from here, so it reads as a warning rather than an error.
  const unconfigured = action.status === 409;

  return (
    <StepCard
      step={5}
      title="Preprocess"
      description="Transforms the eval partition into model input."
      state={preprocessed !== null ? 'done' : preparedId === null ? 'locked' : 'ready'}
      lockedHint="Prepare the partitions first."
    >
      {datasetId === null || preparedId === null ? null : (
        <>
          <div className="work__row">
            <Button
              variant="primary"
              pending={action.pending}
              onClick={() => void action.run(datasetId, preparedId)}
            >
              Preprocess eval partition
            </Button>
          </div>

          {action.error === null ? null : (
            <StatusNote tone={unconfigured ? 'warn' : 'danger'}>{action.error}</StatusNote>
          )}

          {unconfigured && task.preprocessNote !== undefined ? (
            <p className="work__hint">{task.preprocessNote}</p>
          ) : null}

          {preprocessed === null ? null : (
            <Summary
              items={[
                { label: 'Partition', value: preprocessed.partition, mono: true },
                { label: 'Samples', value: preprocessed.sample_count.toLocaleString() },
              ]}
            />
          )}
        </>
      )}
    </StepCard>
  );
}
