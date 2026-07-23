import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAppStore } from '../stores/appStore';
import client from '../api/client';

export interface QueuedItem {
  id: string;
  url: string;
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  data: any;
  createdAt: string;
  retries: number;
}

const QUEUE_STORAGE_KEY = '@deployguard_offline_queue';

export async function getOfflineQueue(): Promise<QueuedItem[]> {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function saveOfflineQueue(queue: QueuedItem[]): Promise<void> {
  try {
    await AsyncStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queue));
    useAppStore.getState().setPendingQueueCount(queue.length);
  } catch (err) {
    console.warn('[OfflineQueue] Failed to save queue:', err);
  }
}

export async function enqueueOfflineRequest(
  url: string,
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  data: any
): Promise<QueuedItem> {
  const queue = await getOfflineQueue();
  const newItem: QueuedItem = {
    id: `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
    url,
    method,
    data,
    createdAt: new Date().toISOString(),
    retries: 0,
  };
  queue.push(newItem);
  await saveOfflineQueue(queue);
  return newItem;
}

export async function flushOfflineQueue(): Promise<{ success: number; failed: number }> {
  const store = useAppStore.getState();
  const queue = await getOfflineQueue();

  if (queue.length === 0) {
    store.setSyncStatus('idle');
    return { success: 0, failed: 0 };
  }

  store.setSyncStatus('syncing');
  let successCount = 0;
  let failedCount = 0;
  const remainingItems: QueuedItem[] = [];

  for (const item of queue) {
    try {
      await client.request({
        url: item.url,
        method: item.method,
        data: item.data,
      });
      successCount++;
    } catch (err: any) {
      console.warn(`[OfflineQueue] Item ${item.id} sync failed:`, err?.message || err);
      item.retries += 1;
      if (item.retries < 5) {
        remainingItems.push(item);
      }
      failedCount++;
    }
  }

  await saveOfflineQueue(remainingItems);

  if (remainingItems.length === 0) {
    store.setSyncStatus('done');
    store.setLastSyncedAt(new Date().toISOString());
    store.triggerRefresh();
  } else {
    store.setSyncStatus('error');
  }

  return { success: successCount, failed: failedCount };
}

// Compatibility exports for legacy code paths
export const flushQueue = flushOfflineQueue;
export const getQueue = getOfflineQueue;
export async function getQueuedRecordIds(): Promise<number[]> {
  const q = await getOfflineQueue();
  return q.map((item) => item.data?.record_id).filter(Boolean);
}
export async function enqueuePresenceMark(data: any): Promise<QueuedItem> {
  return enqueueOfflineRequest('/api/security/mobile/supervisor/mark', 'POST', data);
}
