import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { login as apiLogin, logout as apiLogout, UserProfile } from '../api/auth';
import { updateBaseUrl, loadSessionId, setSessionId } from '../api/client';
import { queryClient } from '../api/queryClient';

const DEFAULT_SERVER_URL = process.env.EXPO_PUBLIC_ODOO_BASE_URL || 'http://47.84.205.81:8069';

interface AuthState {
  isAuthenticated: boolean;
  /** True only during initial bootstrap — NOT set during login. */
  isLoading: boolean;
  isLocked: boolean;
  user: UserProfile | null;
  error: string | null;
  serverUrl: string;

  bootstrap: () => Promise<void>;
  login: (db: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  lock: () => void;
  unlock: () => void;
  setServerUrl: (url: string) => Promise<void>;
  setSession: (sessionId: string, user: UserProfile) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isLoading: true,
  isLocked: false,
  user: null,
  error: null,
  serverUrl: DEFAULT_SERVER_URL,

  bootstrap: async () => {
    try {
      const [profileStr, storedUrl] = await Promise.all([
        SecureStore.getItemAsync('user_profile'),
        SecureStore.getItemAsync('server_url'),
      ]);
      if (storedUrl) {
        updateBaseUrl(storedUrl);
        set({ serverUrl: storedUrl });
      }
      await loadSessionId();
      if (profileStr) {
        set({ isAuthenticated: true, user: JSON.parse(profileStr), isLoading: false });
      } else {
        set({ isAuthenticated: false, user: null, isLoading: false });
      }
    } catch (err) {
      console.error('Auth bootstrap failed', err);
      set({ isAuthenticated: false, user: null, isLoading: false });
    }
  },

  login: async (db, username, password) => {
    // Do NOT set isLoading: true here — the root layout would show a full-screen
    // spinner and hide the login form while the request is in-flight.
    // The login screen manages its own local loading state.
    set({ error: null });
    try {
      const profile = await apiLogin(db, username, password);
      set({ isAuthenticated: true, user: profile, isLocked: false });
    } catch (err: any) {
      set({ error: err.message || 'Login failed. Please verify credentials.' });
      throw err;
    }
  },

  logout: async () => {
    // Clear auth state immediately so the navigation guard redirects at once.
    set({ isAuthenticated: false, user: null, isLocked: false });
    // Flush any cached query data so a re-login as a different role sees fresh data.
    queryClient.clear();
    try {
      await apiLogout();
    } catch (err) {
      console.warn('Backend logout failed', err);
    }
  },

  lock: () => set({ isLocked: true }),

  unlock: () => set({ isLocked: false }),

  setServerUrl: async (url: string) => {
    const clean = url.trim().replace(/\/$/, '');
    updateBaseUrl(clean);
    await SecureStore.setItemAsync('server_url', clean);
    set({ serverUrl: clean });
  },

  setSession: async (sessionId: string, user: UserProfile) => {
    await SecureStore.setItemAsync('user_profile', JSON.stringify(user));
    if (sessionId && sessionId !== 'bypass') {
      await setSessionId(sessionId);
    }
    set({ isAuthenticated: true, user, isLoading: false, error: null });
  },
}));
