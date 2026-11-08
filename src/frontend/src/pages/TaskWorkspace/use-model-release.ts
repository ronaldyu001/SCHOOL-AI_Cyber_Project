/** Release registrations created by this workspace, while leaving borrowed library models alone. */
import { useEffect, useRef } from 'react';
import { deleteModel } from '../../api/models';
import { ApiError } from '../../api/client';

export function useModelRelease() {
  const owned = useRef(new Set<string>());
  const release = async (modelId: string, keepalive = false) => {
    if (!owned.current.has(modelId)) return;
    try {
      await deleteModel(modelId, keepalive);
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 404)) throw error;
    }
    owned.current.delete(modelId);
  };
  const releaseAll = async (keepalive = false) => {
    await Promise.all([...owned.current].map((id) => release(id, keepalive)));
  };
  useEffect(() => {
    // Capture the ref-backed set: it stays current even if cleanup uses the initial closure.
    const releaseOnLeave = () => { void releaseAll(true).catch(() => undefined); };
    window.addEventListener('pagehide', releaseOnLeave);
    return () => {
      window.removeEventListener('pagehide', releaseOnLeave);
      releaseOnLeave();
    };
    // The subscription belongs to the workspace lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { track: (id: string) => owned.current.add(id), release, releaseAll };
}
