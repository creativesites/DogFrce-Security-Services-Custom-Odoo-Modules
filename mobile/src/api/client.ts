import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const DEFAULT_BASE_URL = process.env.EXPO_PUBLIC_ODOO_BASE_URL || 'http://47.84.205.81:8069';

const client = axios.create({
  baseURL: DEFAULT_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: true,
});

export function updateBaseUrl(url: string) {
  client.defaults.baseURL = url.replace(/\/$/, '');
}

// Stores and injects the Odoo session_id explicitly instead of relying on the
// native cookie jar, which behaves inconsistently in Android release builds.
let _sessionId: string | null = null;

export async function setSessionId(id: string | null): Promise<void> {
  _sessionId = id;
  if (id) {
    await SecureStore.setItemAsync('odoo_session_id', id);
  } else {
    await SecureStore.deleteItemAsync('odoo_session_id');
  }
}

export async function loadSessionId(): Promise<void> {
  const stored = await SecureStore.getItemAsync('odoo_session_id');
  _sessionId = stored ?? null;
}

// Inject session_id as both a Cookie header and X-Openerp-Session-Id header.
client.interceptors.request.use((config) => {
  if (_sessionId) {
    config.headers['Cookie'] = `session_id=${_sessionId}`;
    config.headers['X-Openerp-Session-Id'] = _sessionId;
  }
  return config;
});

let _onSessionExpired: (() => void) | null = null;
export function registerSessionExpiredHandler(fn: () => void) {
  _onSessionExpired = fn;
}

export let isOffline = false;

client.interceptors.response.use(
  (response) => {
    isOffline = false;
    const odooError = response.data?.error;
    if (odooError) {
      const msg: string = odooError?.data?.message || odooError?.message || '';
      const isSessionError =
        odooError.code === 100 ||
        msg.toLowerCase().includes('session') ||
        msg.toLowerCase().includes('not logged');
      if (isSessionError) {
        _sessionId = null; // clear immediately so in-flight requests stop retrying
        SecureStore.deleteItemAsync('user_profile').catch(() => {});
        SecureStore.deleteItemAsync('odoo_session_id').catch(() => {});
        _onSessionExpired?.();
        return Promise.reject(new Error('Session expired. Please sign in again.'));
      }
    }
    return response;
  },
  async (error) => {
    if (!error.response) {
      isOffline = true;
      return Promise.reject(error);
    }
    return Promise.reject(error);
  }
);

export default client;
