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

    // Detect Set-Cookie session_id if available
    const setCookie = response.headers?.['set-cookie'] || response.headers?.['Set-Cookie'];
    if (setCookie) {
      const cookieStr = Array.isArray(setCookie) ? setCookie.join(';') : String(setCookie);
      const match = cookieStr.match(/session_id=([^;]+)/);
      if (match && match[1]) {
        setSessionId(match[1]).catch(() => {});
      }
    }

    // Detect Odoo redirecting to HTML login page when session is unauthenticated
    if (typeof response.data === 'string' && (response.data.includes('<!DOCTYPE html>') || response.data.includes('<html'))) {
      _sessionId = null;
      SecureStore.deleteItemAsync('user_profile').catch(() => {});
      SecureStore.deleteItemAsync('odoo_session_id').catch(() => {});
      _onSessionExpired?.();
      return Promise.reject(new Error('Session expired or invalid. Please sign in again.'));
    }

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
      const config = error.config;
      const method = (config?.method || '').toUpperCase();
      const isMutation = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
      const isAuthRoute = config?.url?.includes('/auth/login');

      if (isMutation && !isAuthRoute && config?.url) {
        try {
          const { enqueueOfflineRequest } = await import('../utils/offlineQueue');
          let parsedData = config.data;
          if (typeof parsedData === 'string') {
            try { parsedData = JSON.parse(parsedData); } catch {}
          }
          await enqueueOfflineRequest(config.url, method as any, parsedData);
          return {
            data: {
              success: true,
              queued: true,
              message: 'Offline: Request queued for automatic synchronization.',
            },
            status: 200,
            statusText: 'OK (Queued Offline)',
            headers: {},
            config,
          };
        } catch (enqueueErr) {
          console.warn('[Client] Failed to enqueue offline request:', enqueueErr);
        }
      }
      return Promise.reject(error);
    }
    return Promise.reject(error);
  }
);

export default client;
