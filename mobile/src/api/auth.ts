import client from './client';
import * as SecureStore from 'expo-secure-store';
import { setSessionId } from './client';

export interface UserProfile {
  uid: number;
  name: string;
  username: string;
  db: string;
  role: 'supervisor' | 'manager' | 'owner';
  employee_id: number | null;
}

function mapOdooError(raw: string): string {
  const s = raw.toLowerCase();
  if (s.includes('access denied') || s.includes('invalid credentials') || s.includes('wrong login'))
    return 'Incorrect username or password.';
  if (s.includes('database') || s.includes('db'))
    return 'Database not found. Check your server settings.';
  if (s.includes('network') || s.includes('timeout') || s.includes('econnrefused') || s.includes('enotfound'))
    return 'Cannot reach the server. Check your connection.';
  return raw;
}

export const login = async (db: string, username: string, password: string): Promise<UserProfile> => {
  const response = await client.post('/web/session/authenticate', {
    jsonrpc: '2.0',
    method: 'call',
    params: { db, login: username, password },
  });

  const result = response.data?.result;

  if (!result || !result.uid || response.data.error) {
    const raw =
      response.data?.error?.data?.message ||
      response.data?.error?.message ||
      'Authentication failed. Check your credentials.';
    throw new Error(mapOdooError(raw));
  }

  // Explicitly inject session_id — never rely on the native cookie jar.
  if (result.session_id) {
    await setSessionId(result.session_id);
  }

  // Resolve role from actual Odoo group membership.
  let role: 'supervisor' | 'manager' | 'owner' = 'supervisor';
  let employee_id: number | null = result.partner_id || null;

  try {
    const meResp = await client.get('/api/security/mobile/auth/me');
    if (meResp.data?.success && meResp.data?.data) {
      role = meResp.data.data.role ?? 'supervisor';
      if (meResp.data.data.employee_id) employee_id = meResp.data.data.employee_id;
    }
  } catch {
    // Fallback: string-match — works for demo accounts when endpoint is unreachable.
    const nameLower = (result.name || '').toLowerCase();
    const userLower = username.toLowerCase();
    const isOwner =
      result.is_system ||
      nameLower.includes('owner') ||
      userLower.includes('owner') ||
      nameLower.includes('admin') ||
      userLower.includes('admin');
    const isManager = !isOwner && (nameLower.includes('manager') || userLower.includes('manager'));
    if (isOwner) role = 'owner';
    else if (isManager) role = 'manager';
  }

  const profile: UserProfile = { uid: result.uid, name: result.name, username, db, role, employee_id };
  await SecureStore.setItemAsync('user_profile', JSON.stringify(profile));
  return profile;
};

export const logout = async (): Promise<void> => {
  try {
    await client.post('/web/session/destroy', { jsonrpc: '2.0', method: 'call', params: {} });
  } catch (err) {
    console.warn('Backend session destruction failed', err);
  } finally {
    await SecureStore.deleteItemAsync('user_profile');
    await setSessionId(null);
  }
};
