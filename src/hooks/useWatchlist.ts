import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "finora_watchlist_v1";

export interface WatchlistEntry {
  ticker: string;
  name: string;
  sessionId?: string;
  addedAt: string;
}

export function useWatchlist() {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          setEntries(parsed);
        }
      }
    } catch {
      // ignore malformed data
    }
  }, []);

  // Persist whenever entries change
  const persist = useCallback((list: WatchlistEntry[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch {
      // localStorage full or unavailable
    }
  }, []);

  const add = useCallback(
    (ticker: string, name: string, sessionId?: string) => {
      setEntries((prev) => {
        // Don't duplicate
        if (prev.some((e) => e.ticker === ticker)) return prev;
        const next = [
          ...prev,
          { ticker, name, sessionId, addedAt: new Date().toISOString() },
        ];
        persist(next);
        return next;
      });
    },
    [persist]
  );

  const remove = useCallback(
    (ticker: string) => {
      setEntries((prev) => {
        const next = prev.filter((e) => e.ticker !== ticker);
        persist(next);
        return next;
      });
    },
    [persist]
  );

  const isWatching = useCallback(
    (ticker: string) => entries.some((e) => e.ticker === ticker),
    [entries]
  );

  return { entries, add, remove, isWatching };
}
