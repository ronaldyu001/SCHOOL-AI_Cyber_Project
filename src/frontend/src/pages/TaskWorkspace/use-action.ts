/** Tracks pending/error state for one API call. */
import { useCallback, useContext, useState } from 'react';
import { ActionScopeContext } from './action-scope';
import { ApiError } from '../../api/client';

export interface ActionState<Args extends unknown[]> {
  run: (...args: Args) => Promise<void>;
  pending: boolean;
  error: string | null;
  /** HTTP status of the last failure, so callers can treat 409 as "not ready". */
  status: number | null;
  reset: () => void;
}

export function useAction<Args extends unknown[]>(
  action: (...args: Args) => Promise<void>,
): ActionState<Args> {
  const scope = useContext(ActionScopeContext);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);

  const reset = useCallback(() => {
    setError(null);
    setStatus(null);
  }, []);

  const run = useCallback(
    async (...args: Args) => {
      if (scope !== null && !scope.acquire()) return;
      setPending(true);
      setError(null);
      setStatus(null);
      try {
        await action(...args);
      } catch (caught) {
        if (caught instanceof ApiError) {
          setError(caught.message);
          setStatus(caught.status);
        } else if (caught instanceof Error) {
          setError(caught.message);
        } else {
          setError('Unexpected error');
        }
      } finally {
        setPending(false);
        scope?.release();
      }
    },
    [action, scope],
  );

  return { run, pending, error, status, reset };
}
