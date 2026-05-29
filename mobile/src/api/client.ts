import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

export const ODOO_BASE_URL = 'http://localhost:8069'; // Fallback / Local development

const client = axios.create({
  baseURL: ODOO_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: true, // Necessary for Odoo session cookie management
});

// Intercept requests to inject session header or custom credentials if needed
client.interceptors.request.use(async (config) => {
  try {
    const session = await SecureStore.getItemAsync('odoo_session_id');
    if (session) {
      // In mobile environments, we also pass the Session-Id header just in case,
      // though standard cookie headers handles this automatically if withCredentials is true.
      config.headers['X-Openerp-Session-Id'] = session;
      config.headers['Cookie'] = `session_id=${session}`;
    }
  } catch (err) {
    console.error('Request interceptor SecureStore lookup failed', err);
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Intercept responses to automatically capture or handle auth expiration
client.interceptors.response.use(
  (response) => {
    // If Odoo returns a JSON response containing an error or status=403, we handle it
    if (response.data && response.data.error) {
      console.warn('API returned logic error:', response.data.error);
    }
    return response;
  },
  async (error) => {
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      console.warn('Session expired or unauthorized. Cleared storage.');
      await SecureStore.deleteItemAsync('odoo_session_id');
      await SecureStore.deleteItemAsync('user_profile');
    }
    return Promise.reject(error);
  }
);

export default client;
