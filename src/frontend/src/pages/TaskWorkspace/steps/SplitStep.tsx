import { useState } from 'react';
import { createSplit } from '../../../api/datasets';
import type { SplitRequest, SplitResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, NumberField, StatusNote, Summary } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { useAction } from '../use-action';

const DEFAULT_POLICY: SplitRequest = { seed: 123, train_fraction: 0.7, holdout_test_fraction: 0.5 };

interface SplitStepProps {
  task: TaskDescriptor;
  datasetId: string | null;
  /** Null until the dataset has been cleaned; the backend returns 409 before then. */
  cleaned: boolean;
  split: SplitResponse | null;
  onSplit: (split: SplitResponse) => void;
}

export function SplitStep({ task, datasetId, cleaned, split, onSplit }: SplitStepProps) {
  const [policy, setPolicy] = useState<SplitRequest>(DEFAULT_POLICY);

  const action = useAction(async (id: string) => {
    onSplit(await createSplit(task.slug, id, policy));
  });

  const patch = (change: Partial<SplitRequest>) =>
    setPolicy((current) => ({ ...current, ...change }));

  return (
    <StepCard
      step={3}
      title="Split"
      description="Partitions the cleaned rows into train, test and eval."
      state={split !== null ? 'done' : !cleaned ? 'locked' : 'ready'}
      lockedHint="Clean the dataset first."
    >
      {datasetId === null || !cleaned ? null : (
        <>
          <div className="work__fields">
            <NumberField
              id="split-seed"
              label="Seed"
              hint="0 – 4294967295"
              value={policy.seed}
              min={0}
              max={4294967295}
              step={1}
              onChange={(seed) => patch({ seed })}
            />
            <NumberField
              id="split-train"
              label="Train fraction"
              hint="Share used for training"
              value={policy.train_fraction}
              min={0.01}
              max={0.99}
              step={0.05}
              onChange={(train_fraction) => patch({ train_fraction })}
            />
            <NumberField
              id="split-holdout"
              label="Holdout test fraction"
              hint="Share of the holdout kept for test"
              value={policy.holdout_test_fraction}
              min={0.01}
              max={0.99}
              step={0.05}
              onChange={(holdout_test_fraction) => patch({ holdout_test_fraction })}
            />
          </div>

          <div className="work__row">
            <Button variant="primary" pending={action.pending} onClick={() => void action.run(datasetId)}>
              Create split
            </Button>
            <Button disabled={action.pending} onClick={() => setPolicy(DEFAULT_POLICY)}>
              Reset
            </Button>
          </div>

          {action.error === null ? null : <StatusNote tone="danger">{action.error}</StatusNote>}

          {split === null ? null : (
            <Summary
              items={[
                { label: 'Train', value: split.train_count.toLocaleString() },
                { label: 'Test', value: split.test_count.toLocaleString() },
                { label: 'Eval', value: split.eval_count.toLocaleString() },
                { label: 'Seed', value: split.seed, mono: true },
              ]}
            />
          )}
        </>
      )}
    </StepCard>
  );
}
