import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface AppState {
  selectedDate: string; // YYYY-MM-DD format
  searchQuery: string;
  selectedSiteId: number | null;
  refreshTrigger: number;
  isOffline: boolean;
  lastSyncTime: string | null;

  setSelectedDate: (date: string) => void;
  setSearchQuery: (query: string) => void;
  setSelectedSiteId: (siteId: number | null) => void;
  triggerRefresh: () => void;
  setOffline: (offline: boolean) => void;
  cacheBatch: (batchData: any) => Promise<void>;
  getCachedBatch: () => Promise<any | null>;
}

export const useAppStore = create<AppState>((set) => ({
  selectedDate: new Date().toISOString().split('T')[0],
  searchQuery: '',
  selectedSiteId: null,
  refreshTrigger: 0,
  isOffline: false,
  lastSyncTime: null,

  setSelectedDate: (date) => set({ selectedDate: date }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSelectedSiteId: (siteId) => set({ selectedSiteId: siteId }),
  triggerRefresh: () => set((state) => ({ refreshTrigger: state.refreshTrigger + 1 })),
  setOffline: (offline) => set({ isOffline: offline }),
  cacheBatch: async (batchData) => {
    try {
      await AsyncStorage.setItem('dogforce_batch_cache', JSON.stringify({
        data: batchData,
        timestamp: new Date().toISOString(),
      }));
      set({ lastSyncTime: new Date().toISOString() });
    } catch (e) {
      console.warn('Cache write failed:', e);
    }
  },
  getCachedBatch: async () => {
    try {
      const raw = await AsyncStorage.getItem('dogforce_batch_cache');
      if (!raw) return null;
      const { data, timestamp } = JSON.parse(raw);
      // Cache expires after 4 hours
      const ageMs = Date.now() - new Date(timestamp).getTime();
      if (ageMs > 4 * 60 * 60 * 1000) return null;
      return data;
    } catch (e) {
      return null;
    }
  },
}));
