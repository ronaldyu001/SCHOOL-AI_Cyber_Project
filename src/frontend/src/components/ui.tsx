/** Shared primitives: button, download link, badge, status note, number field, summary list. */
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import './ui.css';

type ButtonVariant = 'primary' | 'secondary' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  pending?: boolean;
}

export function Button({
  variant = 'secondary',
  pending = false,
  disabled,
  children,
  className = '',
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn--${variant} ${className}`.trim()}
      disabled={disabled === true || pending}
      aria-busy={pending || undefined}
      {...rest}
    >
      {pending ? <span className="btn__spinner" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

interface DownloadLinkProps {
  href: string;
  variant?: ButtonVariant;
  /**
   * The surrounding fieldset cannot reach an anchor, so a busy workspace has to
   * disable this itself. Dropping `href` is what actually stops the click.
   */
  disabled?: boolean;
  children: ReactNode;
}

/**
 * A download styled as a button. Deliberately an anchor rather than a fetch:
 * the browser streams the response to disk, and a prepared malware bundle
 * carries the executables themselves, far past what a blob could hold.
 */
export function DownloadLink({ href, variant = 'secondary', disabled = false, children }: DownloadLinkProps) {
  return (
    <a
      className={`btn btn--${variant}`}
      href={disabled ? undefined : href}
      download
      aria-disabled={disabled || undefined}
    >
      {children}
    </a>
  );
}

type Tone = 'neutral' | 'accent' | 'ok' | 'warn' | 'danger';

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

/**
 * Announces async outcomes. Errors use `alert` so they interrupt; everything
 * else uses `status` so it is read after the current utterance.
 */
export function StatusNote({ tone, children }: { tone: Exclude<Tone, 'neutral'>; children: ReactNode }) {
  return (
    <p className={`note note--${tone}`} role={tone === 'danger' ? 'alert' : 'status'}>
      {children}
    </p>
  );
}

interface NumberFieldProps {
  id: string;
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  disabled?: boolean;
  /** Marks the value as out of contract, so the border and assistive tech agree. */
  invalid?: boolean;
  onChange: (value: number) => void;
}

export function NumberField({ id, label, hint, value, min, max, step, disabled, invalid, onChange }: NumberFieldProps) {
  const hintId = hint === undefined ? undefined : `${id}-hint`;
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <input
        className="field__input mono"
        id={id}
        type="number"
        inputMode="decimal"
        value={value}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        aria-invalid={invalid === true || undefined}
        aria-describedby={hintId}
        onChange={(event) => {
          const next = Number(event.target.value);
          if (!Number.isNaN(next)) onChange(next);
        }}
      />
      {hint === undefined ? null : (
        <span className="field__hint" id={hintId}>
          {hint}
        </span>
      )}
    </div>
  );
}

export interface SummaryItem {
  label: string;
  value: ReactNode;
  mono?: boolean;
}

export function Summary({ items }: { items: SummaryItem[] }) {
  return (
    <dl className="summary">
      {items.map((item) => (
        <div className="summary__row" key={item.label}>
          <dt className="summary__label">{item.label}</dt>
          <dd className={`summary__value${item.mono === true ? ' mono' : ''}`}>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
