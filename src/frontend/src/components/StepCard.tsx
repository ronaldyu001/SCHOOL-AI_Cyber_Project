/** One numbered step of the dataset pipeline. Renders as a list item. */
import type { ReactNode } from 'react';
import { Badge } from './ui';
import './StepCard.css';

export type StepState = 'locked' | 'ready' | 'done';

const STATE_LABEL: Record<StepState, string> = {
  locked: 'Locked',
  ready: 'Ready',
  done: 'Done',
};

interface StepCardProps {
  step: number;
  title: string;
  description: string;
  state: StepState;
  /** Why the step is locked. Shown instead of the body when locked. */
  lockedHint?: string;
  children?: ReactNode;
}

export function StepCard({ step, title, description, state, lockedHint, children }: StepCardProps) {
  return (
    <li className={`step step--${state}`}>
      <div className="step__head">
        <span className="step__number" aria-hidden="true">
          {state === 'done' ? '✓' : step}
        </span>
        <div className="step__heading">
          <h2 className="step__title">{title}</h2>
          <p className="step__description">{description}</p>
        </div>
        <Badge tone={state === 'done' ? 'ok' : state === 'ready' ? 'accent' : 'neutral'}>
          {STATE_LABEL[state]}
        </Badge>
      </div>

      <div className="step__body">
        {state === 'locked' ? (
          <p className="step__locked">{lockedHint ?? 'Finish the previous step first.'}</p>
        ) : (
          children
        )}
      </div>
    </li>
  );
}
