/** One active dataset operation per workspace, including resets and unloads. */
import { createContext, useContext, useRef, useState } from 'react';

interface ActionScope {
  busy: boolean;
  acquire: () => boolean;
  release: () => void;
}

export const ActionScopeContext = createContext<ActionScope | null>(null);

export function useActionScope(): ActionScope {
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  return {
    busy,
    acquire: () => {
      if (locked.current) return false;
      locked.current = true;
      setBusy(true);
      return true;
    },
    release: () => {
      locked.current = false;
      setBusy(false);
    },
  };
}

/**
 * Whether any workspace operation is in flight. Steps need this for controls
 * the surrounding fieldset cannot disable, namely the stage download links.
 */
export function useBusy(): boolean {
  return useContext(ActionScopeContext)?.busy ?? false;
}
