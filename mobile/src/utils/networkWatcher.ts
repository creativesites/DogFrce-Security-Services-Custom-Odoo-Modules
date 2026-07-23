/**
 * Singleton NetInfo watcher.
 * - Keeps appStore.isOffline in sync with real connectivity.
 * - Flushes the offline queue and triggers a data refresh when connectivity
 *   is restored after an offline period.
 */
import NetInfo from '@react-native-community/netinfo';
import { useAppStore } from '../stores/appStore';
import { flushQueue } from './offlineQueue';
import { markPresence } from '../api/supervisor';

let _started = false;

export function startNetworkWatcher(): void {
  if (_started) return;
  _started = true;

  NetInfo.addEventListener((state) => {
    const store = useAppStore.getState();
    const wasOffline = store.isOffline;
    const isNowOffline = !state.isConnected || !state.isInternetReachable;

    store.setOffline(isNowOffline ?? false);

    if (wasOffline && !isNowOffline) {
      _autoSync(store);
    }
  });
}

async function _autoSync(store: ReturnType<typeof useAppStore.getState>) {
  store.setSyncStatus('syncing');

  try {
    const result = await flushQueue();
    const remaining = (await import('./offlineQueue')).getOfflineQueue();
    const remainingQueue = await remaining;

    store.setPendingQueueCount(remainingQueue.length);
    store.setLastSyncedAt(new Date().toISOString());
    store.setSyncStatus(result.success > 0 ? 'done' : 'idle');

    if (result.success > 0) {
      // Trigger screens to re-fetch fresh data now that marks are synced
      store.triggerRefresh();
      // Revert banner after 3 s
      setTimeout(() => useAppStore.getState().setSyncStatus('idle'), 3000);
    }
  } catch {
    store.setSyncStatus('error');
  }
}

/** Call once on app start to prime the pending count from storage. */
export async function initPendingCount(): Promise<void> {
  const { getQueue } = await import('./offlineQueue');
  const queue = await getQueue();
  useAppStore.getState().setPendingQueueCount(queue.length);
}
