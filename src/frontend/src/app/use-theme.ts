/**
 * Light/dark theme state.
 *
 * The app follows the operating system until the user picks a theme; from then
 * on the choice is pinned and remembered. The matching data-theme is applied in
 * index.html before first paint, so this hook only keeps it in step.
 */
import { useCallback, useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'theme';
const DARK_QUERY = '(prefers-color-scheme: dark)';

/** Storage can throw in private mode, so every access is guarded. */
function readStored(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

function readSystem(): Theme {
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light';
}

export function useTheme(): { theme: Theme; toggle: () => void } {
  const [pinned, setPinned] = useState(() => readStored() !== null);
  const [theme, setTheme] = useState<Theme>(() => readStored() ?? readSystem());

  // Track the system preference until the user overrides it.
  useEffect(() => {
    if (pinned) return;
    const query = window.matchMedia(DARK_QUERY);
    const sync = (event: MediaQueryListEvent) => setTheme(event.matches ? 'dark' : 'light');
    query.addEventListener('change', sync);
    return () => query.removeEventListener('change', sync);
  }, [pinned]);

  // Mirror onto <html>; absent means "follow the system".
  useEffect(() => {
    const root = document.documentElement;
    if (pinned) root.dataset.theme = theme;
    else delete root.dataset.theme;
  }, [theme, pinned]);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // A remembered theme is a convenience; carry on without it.
      }
      return next;
    });
    setPinned(true);
  }, []);

  return { theme, toggle };
}
