import { useState } from 'react';
import { createSplit } from '../../../api/datasets';
import type { SplitRequest, SplitResponse } from '../../../api/types';
import { StepCard } from '../../../components/StepCard';
import { Button, NumberField, StatusNote, Summary } from '../../../components/ui';
import type { TaskDescriptor } from '../../../tasks/catalog';
import { useAction } from '../use-action';

const DEFAULT_POLICY: SplitRequest = { seed: 123, train_fraction: 0.7, test_fraction: 0.15, eval_fraction: 0.15 };

/** The same bound and tolerance SplitRequest applies in schemas.py. */
const TOLERANCE = 1e-9;
const outOfRange = (value: number) => !Number.isFinite(value) || value <= 0 || value >= 1;

const percent = (value: number) =>
  Number.isFinite(value) ? `${Math.round(value * 1000) / 10}%` : '—';

/**
 * A total rejected for being a hair off one still rounds to a flat 100% at the
 * breakdown's precision, so reporting it that way would contradict the warning
 * carrying it. This keeps enough digits to show what was actually wrong.
 */
const exactPercent = (value: number) =>
  Number.isFinite(value) ? `${Number((value * 100).toPrecision(6))}%` : '—';

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

  const fractions = [policy.train_fraction, policy.test_fraction, policy.eval_fraction];
  const total = fractions.reduce((sum, value) => sum + value, 0);
  // Kept apart because a fraction can be out of range while the three still
  // total one, and then only the range explains the rejection.
  const anyOutOfRange = fractions.some(outOfRange);
  const totalIsOff = Math.abs(total - 1) > TOLERANCE;
  const invalidPolicy = anyOutOfRange || totalIsOff;
  const breakdown = `${percent(policy.train_fraction)} train · ${percent(policy.test_fraction)} test · ${percent(policy.eval_fraction)} eval`;

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
              hint="Share of the full dataset used for training"
              value={policy.train_fraction}
              min={0.01}
              max={0.99}
              step={0.05}
              invalid={outOfRange(policy.train_fraction)}
              onChange={(train_fraction) => patch({ train_fraction })}
            />
            <NumberField
              id="split-test"
              label="Test fraction"
              hint="Share of the full dataset used for test"
              value={policy.test_fraction}
              min={0.01}
              max={0.99}
              step={0.05}
              invalid={outOfRange(policy.test_fraction)}
              onChange={(test_fraction) => patch({ test_fraction })}
            />
            <NumberField
              id="split-eval"
              label="Eval fraction"
              hint="Share of the full dataset used for evaluation"
              value={policy.eval_fraction}
              min={0.01}
              max={0.99}
              step={0.05}
              invalid={outOfRange(policy.eval_fraction)}
              onChange={(eval_fraction) => patch({ eval_fraction })}
            />
          </div>

          {invalidPolicy ? (
            <StatusNote tone="warn">
              {anyOutOfRange
                ? 'Each fraction must be above 0 and below 1.'
                : `Train, test and eval must total 100%; these total ${exactPercent(total)}.`}
            </StatusNote>
          ) : (
            <p className="work__hint">{`Gives ${breakdown}.`}</p>
          )}

          <div className="work__row">
            <Button
              variant="primary"
              pending={action.pending}
              disabled={invalidPolicy}
              onClick={() => void action.run(datasetId)}
            >
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
