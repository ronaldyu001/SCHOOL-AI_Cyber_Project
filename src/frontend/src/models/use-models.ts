/**
 * The uploaded model registry.
 *
 * Models belong to the application rather than to a dataset session, so both
 * the models page and the workspace's predict step read the same list.
 */
import { useCallback, useEffect, useState } from 'react';
import { listModels } from '../api/models';
import type { UploadedModel } from '../api/types';

export interface ModelRegistry {
  models: UploadedModel[];
  error: string | null;
  loading: boolean;
  reload: () => void;
}

export function useModels(): ModelRegistry {
  const [models, setModels] = useState<UploadedModel[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    listModels(controller.signal)
      .then((result) => {
        setModels(result);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setError(caught instanceof Error ? caught.message : 'Unexpected error');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [revision]);

  // Loading is raised here rather than in the effect, which may not call
  // setState synchronously; the first load starts from the initial state.
  const reload = useCallback(() => {
    setLoading(true);
    setRevision((current) => current + 1);
  }, []);

  return { models, error, loading, reload };
}
