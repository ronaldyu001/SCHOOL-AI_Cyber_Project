import { prepareDataset } from '../../../api/datasets';
import type { PrepareResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, StatusNote, Summary } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { useAction } from '../use-action';

interface PrepareStepProps {
  task: TaskDescriptor;
  datasetId: string | null;
  splitId: string | null;
  prepared: PrepareResponse | null;
  onPrepared: (prepared: PrepareResponse) => void;
}

export function PrepareStep({ task, datasetId, splitId, prepared, onPrepared }: PrepareStepProps) {
  const action = useAction(async (id: string, split: string) => {
    onPrepared(await prepareDataset(task.slug, id, split));
  });

  return (
    <StepCard
      step={4}
      title="Prepare"
      description="Materialises the records of each partition in split order."
      state={prepared !== null ? 'done' : splitId === null ? 'locked' : 'ready'}
      lockedHint="Create a split first."
    >
      {datasetId === null || splitId === null ? null : (
        <>
          <div className="work__row">
            <Button
              variant="primary"
              pending={action.pending}
              onClick={() => void action.run(datasetId, splitId)}
            >
              Prepare partitions
            </Button>
          </div>

          {action.error === null ? null : <StatusNote tone="danger">{action.error}</StatusNote>}

          {prepared === null ? null : (
            <Summary
              items={[
                { label: 'Train', value: prepared.train_count.toLocaleString() },
                { label: 'Test', value: prepared.test_count.toLocaleString() },
                { label: 'Eval', value: prepared.eval_count.toLocaleString() },
              ]}
            />
          )}
        </>
      )}
    </StepCard>
  );
}
