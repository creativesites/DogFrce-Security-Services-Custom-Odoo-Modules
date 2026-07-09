/**
 * Generic TTL cache backed by AsyncStorage.
 * Keys are namespaced under "dg_cache_" to avoid collisions.
 * All reads are safe — a miss or parse error returns null.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

const PREFIX = 'dg_cache_';
const DEFAULT_TTL_MS = 4 * 60 * 60 * 1000; // 4 hours

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

export interface CacheResult<T> {
  data: T;
  cachedAt: number;   // unix ms
  stale: boolean;     // true when within TTL but server wasn't reachable
}

export async function cacheSet<T>(key: string, data: T): Promise<void> {
  try {
    const entry: CacheEntry<T> = { data, timestamp: Date.now() };
    await AsyncStorage.setItem(PREFIX + key, JSON.stringify(entry));
  } catch {
    // Storage write failure is non-fatal
  }
}

export async function cacheGet<T>(
  key: string,
  maxAgeMs = DEFAULT_TTL_MS
): Promise<CacheResult<T> | null> {
  try {
    const raw = await AsyncStorage.getItem(PREFIX + key);
    if (!raw) return null;
    const entry: CacheEntry<T> = JSON.parse(raw);
    const age = Date.now() - entry.timestamp;
    if (age > maxAgeMs) return null; // expired — don't serve
    return { data: entry.data, cachedAt: entry.timestamp, stale: false };
  } catch {
    return null;
  }
}

/** Returns stale (expired) data — used when offline and no fresh data is available. */
export async function cacheGetStale<T>(key: string): Promise<CacheResult<T> | null> {
  try {
    const raw = await AsyncStorage.getItem(PREFIX + key);
    if (!raw) return null;
    const entry: CacheEntry<T> = JSON.parse(raw);
    return { data: entry.data, cachedAt: entry.timestamp, stale: true };
  } catch {
    return null;
  }
}

export async function cacheClear(key: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(PREFIX + key);
  } catch {}
}
