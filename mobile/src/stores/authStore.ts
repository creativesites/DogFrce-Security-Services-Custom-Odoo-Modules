import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { login as apiLogin, logout as apiLogout, UserProfile } from '../api/auth';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserProfile | null;
  error: string | null;

  bootstrap: () => Promise<void>;
  login: (db: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setSession: (sessionId: string, user: UserProfile) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isLoading: true,
  user: null,
  error: null,

  bootstrap: async () => {
    try {
      const session = await SecureStore.getItemAsync('odoo_session_id');
      const profileStr = await SecureStore.getItemAsync('user_profile');

      if (session && profileStr) {
        set({
          isAuthenticated: true,
          user: JSON.parse(profileStr),
          isLoading: false,
        });
      } else {
        set({ isAuthenticated: false, user: null, isLoading: false });
      }
    } catch (err) {
      console.error('Auth store bootstrapping failed', err);
      set({ isAuthenticated: false, user: null, isLoading: false });
    }
  },

  login: async (db, username, password) => {
    set({ isLoading: true, error: null });
    try {
      const profile = await apiLogin(db, username, password);
      set({
        isAuthenticated: true,
        user: profile,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err.message || 'Login failed. Please verify credentials.',
      });
      throw err;
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await apiLogout();
    } catch (err) {
      console.warn('Backend logout failed', err);
    } finally {
      set({
        isAuthenticated: false,
        user: null,
        isLoading: false,
      });
    }
  },

  setSession: async (sessionId: string, user: UserProfile) => {
    await SecureStore.setItemAsync('odoo_session_id', sessionId);
    await SecureStore.setItemAsync('user_profile', JSON.stringify(user));
    set({ isAuthenticated: true, user, isLoading: false, error: null });
  },
}));
