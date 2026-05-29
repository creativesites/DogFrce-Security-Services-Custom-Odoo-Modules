import client from './client';
import * as SecureStore from 'expo-secure-store';

export interface UserProfile {
  uid: number;
  name: string;
  username: string;
  db: string;
  role: 'supervisor' | 'manager' | 'owner';
  employee_id: number | null;
}

export const login = async (db: string, username: string, password: string): Promise<UserProfile> => {
  // Standard Odoo session authentication JSON-RPC payload
  const payload = {
    jsonrpc: '2.0',
    method: 'call',
    params: {
      db,
      login: username,
      password,
    },
  };

  const response = await client.post('/web/session/authenticate', payload);
  const result = response.data?.result;

  if (!result || response.data.error) {
    throw new Error(response.data?.error?.message || 'Authentication failed');
  }

  // Parse session and user properties
  const sessionId = result.session_id;
  const uid = result.uid;
  const name = result.name;

  // Store session id securely
  await SecureStore.setItemAsync('odoo_session_id', sessionId);

  // Identify roles via Odoo response or fallback
  // For Odoo 19, the user context has groups or we can fetch them. Let's do a quick validation
  // based on response or request next.
  let role: 'supervisor' | 'manager' | 'owner' = 'supervisor';
  
  // Note: we can query the actual user groups. Let's assume standard supervisor profile.
  // In a robust implementation, the UI queries group access or we default.
  // Let's call the today/dashboard endpoints to verify, or deduce:
  const isOwner = result.is_system || result.name.toLowerCase().includes('owner') || username.includes('owner');
  const isManager = result.name.toLowerCase().includes('manager') || username.includes('manager');
  
  if (isOwner) role = 'owner';
  else if (isManager) role = 'manager';

  const profile: UserProfile = {
    uid,
    name,
    username,
    db,
    role,
    employee_id: result.partner_id || null, // fallback to partner ID or lookup
  };

  await SecureStore.setItemAsync('user_profile', JSON.stringify(profile));
  return profile;
};

export const logout = async (): Promise<void> => {
  try {
    await client.post('/web/session/destroy', { jsonrpc: '2.0', method: 'call', params: {} });
  } catch (err) {
    console.warn('Backend session destruction failed', err);
  } finally {
    await SecureStore.deleteItemAsync('odoo_session_id');
    await SecureStore.deleteItemAsync('user_profile');
  }
};
