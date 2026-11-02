/**
 * In-memory Stale-While-Revalidate (SWR) query cache for DeployGuard Desktop.
 *
 * Provides:
 * - 0ms perceived latency on tab / page switches by immediately returning cached data.
 * - Silent background revalidation when cached data is older than `staleTime`.
 * - In-flight request deduplication (prevents redundant IPC calls when multiple
 *   components or rapidly switching views request the same data).
 * - Targeted cache invalidation (e.g. invalidateQueries("today") when a task is updated).
 * - Automatic reset on sign-out / user switch.
 */

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  status: "success" | "error";
  error?: unknown;
}

export interface QueryOptions {
  /** Time in ms before cached data is considered stale. Default: 30,000 (30s). */
  staleTime?: number;
  /** Force refetch even if data is still fresh. Default: false. */
  force?: boolean;
}

export interface UseQueryOptions<T> {
  /** Time in ms before cached data is considered stale. Default: 30,000 (30s). */
  staleTime?: number;
  /** Whether the query is enabled. Default: true. */
  enabled?: boolean;
  /** Bumped by UI reload triggers to force a background refetch. */
  reloadSignal?: number;
  /** Callback fired when fresh data arrives. */
  onSuccess?: (data: T) => void;
  /** Callback fired on error. */
  onError?: (err: unknown) => void;
}

export interface UseQueryResult<T> {
  data: T | null;
  error: unknown | null;
  /** True ONLY when there is no cached data at all and an initial fetch is running. */
  isLoading: boolean;
  /** True whenever a network fetch is in-flight (initial or background revalidation). */
  isFetching: boolean;
  /** Whether the current data is older than staleTime. */
  isStale: boolean;
  /** Force an immediate refresh. */
  refetch: () => Promise<T | null>;
}

const DEFAULT_STALE_TIME = 30_000;

// Internal stores
const cache = new Map<string, CacheEntry<unknown>>();
const inFlight = new Map<string, Promise<unknown>>();
const listeners = new Map<string, Set<() => void>>();

let globalFetchingCount = 0;
let lastSyncedAt = Date.now();
const globalListeners = new Set<() => void>();

function notifyGlobal() {
  for (const listener of globalListeners) {
    try {
      listener();
    } catch {
      // Ignore
    }
  }
}

export function subscribeGlobalSync(listener: () => void): () => void {
  globalListeners.add(listener);
  return () => {
    globalListeners.delete(listener);
  };
}

export function getIsSyncing(): boolean {
  return globalFetchingCount > 0;
}

export function getLastSyncedAt(): number {
  return lastSyncedAt;
}

/** Hook to observe if any query cache revalidations are currently in-flight. */
export function useIsSyncing(): boolean {
  return useSyncExternalStore(
    subscribeGlobalSync,
    getIsSyncing,
    () => false,
  );
}

/** Hook to observe the timestamp of the last successful query revalidation. */
export function useLastSyncedAt(): number {
  return useSyncExternalStore(
    subscribeGlobalSync,
    getLastSyncedAt,
    () => lastSyncedAt,
  );
}

function notify(key: string) {
  const set = listeners.get(key);
  if (set) {
    for (const listener of set) {
      try {
        listener();
      } catch {
        // Listener errors shouldn't break the cache
      }
    }
  }
}

function subscribe(key: string, listener: () => void): () => void {
  let set = listeners.get(key);
  if (!set) {
    set = new Set();
    listeners.set(key, set);
  }
  set.add(listener);
  return () => {
    set?.delete(listener);
    if (set && set.size === 0) {
      listeners.delete(key);
    }
  };
}

/** Synchronously retrieve an entry from the cache. */
export function getQueryData<T>(key: string): T | null {
  const entry = cache.get(key);
  if (entry && entry.status === "success") {
    return entry.data as T;
  }
  return null;
}

/** Synchronously retrieve the full cache entry including metadata. */
export function getQueryEntry<T>(key: string): CacheEntry<T> | null {
  const entry = cache.get(key);
  return (entry as CacheEntry<T>) || null;
}

/** Manually set or optimistically update query cache data. */
export function setQueryData<T>(key: string, dataOrUpdater: T | ((prev: T | null) => T)): void {
  const prev = getQueryData<T>(key);
  const data = typeof dataOrUpdater === "function"
    ? (dataOrUpdater as (prev: T | null) => T)(prev)
    : dataOrUpdater;

  cache.set(key, {
    data,
    timestamp: Date.now(),
    status: "success",
  });
  notify(key);
}

/**
 * Invalidate cached queries by exact key or prefix.
 * Matched queries are marked stale (`timestamp = 0`) and their active
 * subscribers are notified to refetch.
 */
export function invalidateQueries(prefix?: string): void {
  const matchedKeys: string[] = [];
  for (const key of cache.keys()) {
    if (!prefix || key === prefix || key.startsWith(`${prefix}:`) || key.startsWith(prefix)) {
      const entry = cache.get(key);
      if (entry) {
        entry.timestamp = 0; // Mark stale
        matchedKeys.push(key);
      }
    }
  }
  for (const key of matchedKeys) {
    notify(key);
  }
}

/** Clear all cache entries, in-flight promises, and subscriptions. Used on logout. */
export function clearQueryCache(): void {
  cache.clear();
  inFlight.clear();
  globalFetchingCount = 0;
  for (const set of listeners.values()) {
    for (const listener of set) {
      try {
        listener();
      } catch {
        // Ignore
      }
    }
  }
  listeners.clear();
  notifyGlobal();
}

/**
 * Execute a query with caching and in-flight request deduplication.
 */
export async function fetchWithCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: QueryOptions = {},
): Promise<T> {
  const staleTime = options.staleTime ?? DEFAULT_STALE_TIME;
  const entry = cache.get(key);

  // Return fresh cached data unless force is requested
  if (!options.force && entry && entry.status === "success") {
    const isFresh = Date.now() - entry.timestamp < staleTime;
    if (isFresh) {
      return entry.data as T;
    }
  }

  // Deduplicate concurrent in-flight requests for the exact same key
  const existing = inFlight.get(key);
  if (existing) {
    return existing as Promise<T>;
  }

  globalFetchingCount++;
  notifyGlobal();

  const promise = (async () => {
    try {
      const data = await fetcher();
      cache.set(key, {
        data,
        timestamp: Date.now(),
        status: "success",
      });
      lastSyncedAt = Date.now();
      notify(key);
      return data;
    } catch (err) {
      // If we had stale data, preserve it so the screen doesn't break,
      // but record the error on the entry
      const prev = cache.get(key);
      if (!prev || prev.status !== "success") {
        cache.set(key, {
          data: null,
          timestamp: Date.now(),
          status: "error",
          error: err,
        });
      }
      notify(key);
      throw err;
    } finally {
      inFlight.delete(key);
      globalFetchingCount = Math.max(0, globalFetchingCount - 1);
      notifyGlobal();
    }
  })();

  inFlight.set(key, promise);
  return promise;
}

/**
 * React hook for Stale-While-Revalidate data fetching.
 *
 * Guarantees:
 * - If cached data exists: returns immediately on mount (0ms latency, `isLoading === false`).
 * - If data is stale: silently triggers background revalidation without clearing existing data.
 * - If no data exists: `isLoading === true`.
 * - `refetch()` or bumps to `reloadSignal` force a background update.
 */
export function useQuery<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  options: UseQueryOptions<T> = {},
): UseQueryResult<T> {
  const {
    staleTime = DEFAULT_STALE_TIME,
    enabled = true,
    reloadSignal,
    onSuccess,
    onError,
  } = options;

  // Subscribe to cache updates for this key
  const entry = useSyncExternalStore(
    (onStoreChange) => (key ? subscribe(key, onStoreChange) : () => {}),
    () => (key ? getQueryEntry<T>(key) : null),
  );

  const [isFetching, setIsFetching] = useState(false);
  const [fetchError, setFetchError] = useState<unknown | null>(null);

  const cachedData = entry && entry.status === "success" ? entry.data : null;
  const isStale = !entry || Date.now() - entry.timestamp >= staleTime;
  const isLoading = enabled && Boolean(key) && cachedData === null && isFetching;

  // Keep latest callbacks in refs to avoid re-triggering effects
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const onSuccessRef = useRef(onSuccess);
  onSuccessRef.current = onSuccess;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const executeFetch = useRef(async (force = false): Promise<T | null> => {
    if (!key || !enabled) return null;
    setIsFetching(true);
    setFetchError(null);
    try {
      const fresh = await fetchWithCache<T>(key, () => fetcherRef.current(), { staleTime, force });
      onSuccessRef.current?.(fresh);
      return fresh;
    } catch (err) {
      setFetchError(err);
      onErrorRef.current?.(err);
      return null;
    } finally {
      setIsFetching(false);
    }
  });

  // Revalidate on mount or key change if stale/missing
  useEffect(() => {
    if (!key || !enabled) return;
    const currentEntry = getQueryEntry<T>(key);
    const needsFetch = !currentEntry || Date.now() - currentEntry.timestamp >= staleTime;
    if (needsFetch) {
      void executeFetch.current(false);
    }
  }, [key, enabled, staleTime]);

  // Revalidate on reloadSignal change
  const firstSignal = useRef(true);
  useEffect(() => {
    if (firstSignal.current) {
      firstSignal.current = false;
      return;
    }
    if (key && enabled) {
      void executeFetch.current(true);
    }
  }, [reloadSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  const refetch = () => executeFetch.current(true);

  return {
    data: cachedData,
    error: fetchError || (entry?.status === "error" ? entry.error : null),
    isLoading,
    isFetching,
    isStale,
    refetch,
  };
}
