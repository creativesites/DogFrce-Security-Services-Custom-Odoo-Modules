import { useState, useEffect, useRef, useCallback } from 'react';
import { cacheGet, cacheSet, cacheGetStale } from '../utils/apiCache';
import { useAppStore } from '../stores/appStore';

export interface OfflineQueryResult<T> {
  data: T | null;
  isLoading: boolean;
  isRefreshing: boolean;
  isStale: boolean;
  cachedAt: number | null;
  error: string | null;
  refetch: () => void;
}

/**
 * Cache-first data fetching hook with offline support.
 *
 * Behaviour:
 * 1. Immediately shows valid cached data (no loading flash if cache warm)
 * 2. Fetches fresh data in the background
 * 3. When offline: serves stale cache if available; error only if nothing cached
 * 4. When cacheKey changes (e.g. month picker): resets and re-fetches
 */
export function useOfflineQuery<T>(
  cacheKey: string,
  fetcher: () => Promise<T>,
  ttlMs = 4 * 60 * 60 * 1000,
): OfflineQueryResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isStale, setIsStale] = useState(false);
  const [cachedAt, setCachedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Refs so execute() never becomes stale without changing identity
  const isOfflineRef = useRef(useAppStore.getState().isOffline);
  const fetcherRef = useRef(fetcher);
  const hasDataRef = useRef(false);
  fetcherRef.current = fetcher;

  // Keep isOfflineRef in sync with the store
  useEffect(() =>
    useAppStore.subscribe((s) => { isOfflineRef.current = s.isOffline; }),
  []);

  const execute = useCallback(async (isRefresh: boolean) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else if (!hasDataRef.current) {
      setIsLoading(true);
    }

    // Step 1 — serve valid cache immediately
    const cached = await cacheGet<T>(cacheKey, ttlMs);
    if (cached) {
      setData(cached.data);
      setCachedAt(cached.cachedAt);
      hasDataRef.current = true;
      setIsLoading(false);
      setIsStale(false);
      setError(null);
    } else if (!hasDataRef.current) {
      // Step 2 — while waiting for network, show stale cache if any
      const stale = await cacheGetStale<T>(cacheKey);
      if (stale) {
        setData(stale.data);
        setCachedAt(stale.cachedAt);
        hasDataRef.current = true;
        setIsLoading(false);
        setIsStale(true);
        setError(null);
      }
    }

    // Step 3 — fetch fresh (even when cache hit, to stay current)
    if (!isOfflineRef.current) {
      try {
        const fresh = await fetcherRef.current();
        setData(fresh);
        hasDataRef.current = true;
        setIsStale(false);
        setError(null);
        setIsLoading(false);
        const now = Date.now();
        setCachedAt(now);
        await cacheSet(cacheKey, fresh);
      } catch (err: any) {
        if (!hasDataRef.current) {
          setError(err.message || 'Failed to load. Pull down to retry.');
          setIsLoading(false);
        } else {
          setIsStale(true); // silent: already showing data
        }
      }
    } else {
      if (!hasDataRef.current) {
        setError("You're offline and there's no cached data available.");
        setIsLoading(false);
      }
    }

    setIsRefreshing(false);
  }, [cacheKey, ttlMs]);

  // Reset and re-fetch when cacheKey changes (e.g. month/date picker)
  useEffect(() => {
    hasDataRef.current = false;
    setData(null);
    setCachedAt(null);
    setIsLoading(true);
    setIsStale(false);
    setError(null);
    execute(false);
  }, [cacheKey, execute]);

  // Silently refetch when coming back online
  useEffect(() =>
    useAppStore.subscribe((s, prev) => {
      if (prev.isOffline && !s.isOffline) execute(true);
    }),
  [execute]);

  return {
    data,
    isLoading,
    isRefreshing,
    isStale,
    cachedAt,
    error,
    refetch: () => execute(true),
  };
}
