import type { JobStatus } from '../api/jobs';
import { Button, StatusNote } from '../components/ui';

export function JobProgress({ job, error, onCancel }: { job: JobStatus | null; error: string | null; onCancel: () => Promise<void> }) {
  if (job === null) return error === null ? null : <StatusNote tone="danger">{error}</StatusNote>;
  const active = ['queued', 'running', 'cancelling'].includes(job.status);
  const phase = job.phase.replaceAll('_', ' ');
  return <div className="work__job" aria-live="polite">
    <p className="work__hint">{job.status === 'queued' ? 'Queued — waiting for the current operation to finish.'
      : `${phase.charAt(0).toUpperCase()}${phase.slice(1)}${job.total > 0 ? ` · ${job.completed.toLocaleString()} / ${job.total.toLocaleString()}` : ''} · ${job.percent}%`}</p>
    <progress aria-label={`${job.kind} progress`} value={job.percent} max={100} />
    {active ? <div className="work__row"><Button disabled={job.status === 'cancelling'} onClick={() => void onCancel()}>
      {job.status === 'cancelling' ? 'Cancelling…' : 'Cancel operation'}
    </Button></div> : null}
    {error === null ? null : <StatusNote tone={job.status === 'cancelled' ? 'warn' : 'danger'}>{error}</StatusNote>}
  </div>;
}
