import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type SyncStatus = 'idle' | 'syncing' | 'done' | 'error';

interface AppState {
  selectedDate: string; // YYYY-MM-DD
  searchQuery: string;
  selectedSiteId: number | null;
  refreshTrigger: number;
  isOffline: boolean;
  lastSyncedAt: string | null;
  syncStatus: SyncStatus;
  pendingQueueCount: number;

  setSelectedDate: (date: string) => void;
  setSearchQuery: (query: string) => void;
  setSelectedSiteId: (siteId: number | null) => void;
  triggerRefresh: () => void;
  setOffline: (offline: boolean) => void;
  setSyncStatus: (status: SyncStatus) => void;
  setLastSyncedAt: (ts: string) => void;
  setPendingQueueCount: (n: number) => void;
  cacheBatch: (batchData: any) => Promise<void>;
  getCachedBatch: () => Promise<any | null>;
}

export const useAppStore = create<AppState>((set) => ({
  selectedDate: new Date().toISOString().split('T')[0],
  searchQuery: '',
  selectedSiteId: null,
  refreshTrigger: 0,
  isOffline: false,
  lastSyncedAt: null,
  syncStatus: 'idle',
  pendingQueueCount: 0,

  setSelectedDate: (date) => set({ selectedDate: date }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSelectedSiteId: (siteId) => set({ selectedSiteId: siteId }),
  triggerRefresh: () => set((state) => ({ refreshTrigger: state.refreshTrigger + 1 })),
  setOffline: (offline) => set({ isOffline: offline }),
  setSyncStatus: (status) => set({ syncStatus: status }),
  setLastSyncedAt: (ts) => set({ lastSyncedAt: ts }),
  setPendingQueueCount: (n) => set({ pendingQueueCount: n }),

  cacheBatch: async (batchData) => {
    try {
      await AsyncStorage.setItem('deployguard_batch_cache', JSON.stringify({
        data: batchData,
        timestamp: new Date().toISOString(),
      }));
      set({ lastSyncedAt: new Date().toISOString() });
    } catch (e) {
      console.warn('Cache write failed:', e);
    }
  },

  getCachedBatch: async () => {
    try {
      const raw = await AsyncStorage.getItem('deployguard_batch_cache');
      if (!raw) return null;
      const { data, timestamp } = JSON.parse(raw);
      const ageMs = Date.now() - new Date(timestamp).getTime();
      if (ageMs > 4 * 60 * 60 * 1000) return null;
      return data;
    } catch {
      return null;
    }
  },
}));
