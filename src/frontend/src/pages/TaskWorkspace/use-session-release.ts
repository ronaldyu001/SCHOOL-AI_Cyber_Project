/**
 * Releases the backend's dataset session once the console stops using it.
 *
 * A session is held in the API process until something deletes it, so a
 * workspace that is simply navigated away from — a task change, a return to the
 * task list, a closed tab — would leave its loaded dataset resident for the
 * life of the server.
 *
 * `hold` stops that. Unloading a dataset also deletes the predictions saved
 * from it, so once this session has produced one, freeing memory is no longer
 * the frontend's call to make silently: the user unloads deliberately instead.
 */
import { useEffect, useRef } from 'react';
import { releaseDataset, type TaskSlug } from '../../api/datasets';

export function useSessionRelease(slug: TaskSlug, datasetId: string | null, hold = false) {
  const active = useRef<string | null>(null);

  useEffect(() => {
    active.current = hold ? null : datasetId;
  }, [datasetId, hold]);

  useEffect(() => {
    const release = () => {
      const id = active.current;
      active.current = null;
      if (id !== null) void releaseDataset(slug, id);
    };

    // A closing or reloading tab never unmounts, so the same release hangs off
    // `pagehide` as well; clearing the ref first is what keeps the two paths
    // from each sending their own delete.
    window.addEventListener('pagehide', release);
    return () => {
      window.removeEventListener('pagehide', release);
      release();
    };
  }, [slug]);
}
