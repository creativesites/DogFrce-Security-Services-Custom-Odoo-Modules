import { create } from 'zustand';

interface AppState {
  selectedDate: string; // YYYY-MM-DD format
  searchQuery: string;
  selectedSiteId: number | null;
  refreshTrigger: number;
  
  setSelectedDate: (date: string) => void;
  setSearchQuery: (query: string) => void;
  setSelectedSiteId: (siteId: number | null) => void;
  triggerRefresh: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedDate: new Date().toISOString().split('T')[0],
  searchQuery: '',
  selectedSiteId: null,
  refreshTrigger: 0,

  setSelectedDate: (date) => set({ selectedDate: date }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSelectedSiteId: (siteId) => set({ selectedSiteId: siteId }),
  triggerRefresh: () => set((state) => ({ refreshTrigger: state.refreshTrigger + 1 })),
}));
