import { prepareDataset } from '../../../api/datasets';
import type { PrepareResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, StatusNote, Summary } from '../../../components/ui';
import { recordNote, type TaskDescriptor } from '../../../tasks/catalog';
import { StageDownload } from '../StageDownload';
import { useAction } from '../use-action';

interface PrepareStepProps {
  onReset?: () => void;
  task: TaskDescriptor;
  datasetId: string | null;
  splitId: string | null;
  prepared: PrepareResponse | null;
  onPrepared: (prepared: PrepareResponse) => void;
}

export function PrepareStep({ onReset, task, datasetId, splitId, prepared, onPrepared }: PrepareStepProps) {
  const action = useAction(async (id: string, split: string) => {
    onPrepared(await prepareDataset(task.slug, id, split));
  });

  return (
    <StepCard onReset={onReset}
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
            <>
              <Summary
                items={[
                  { label: 'Train', value: prepared.train_count.toLocaleString() },
                  { label: 'Test', value: prepared.test_count.toLocaleString() },
                  { label: 'Eval', value: prepared.eval_count.toLocaleString() },
                ]}
              />
              <StageDownload
                slug={task.slug}
                datasetId={datasetId}
                stage="prepared"
                resultId={prepared.prepared_id}
                byPartition
                label="Download prepared records (.zip)"
                contents={`Records in split order, one folder per partition.${recordNote(task)}`}
              />
            </>
          )}
        </>
      )}
    </StepCard>
  );
}
