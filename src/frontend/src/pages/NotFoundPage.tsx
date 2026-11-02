import { Link } from 'react-router-dom';

export function NotFoundPage({ message = 'That page does not exist.' }: { message?: string }) {
  return (
    <section>
      <h1>Not found</h1>
      <p style={{ marginTop: 'var(--space-2)', color: 'var(--text-muted)' }}>{message}</p>
      <p style={{ marginTop: 'var(--space-4)' }}>
        <Link to="/">Back to task selection</Link>
      </p>
    </section>
  );
}
