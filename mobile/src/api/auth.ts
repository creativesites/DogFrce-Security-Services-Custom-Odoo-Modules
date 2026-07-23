import client from './client';
import * as SecureStore from 'expo-secure-store';
import { setSessionId } from './client';

export interface UserProfile {
  uid: number;
  name: string;
  username: string;
  db: string;
  role: 'supervisor' | 'manager' | 'owner' | 'guard';
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
  let sessionId: string | null = null;
  let profileData: Partial<UserProfile> = {};

  try {
    // 1. Try dedicated REST mobile login endpoint
    const res = await client.post('/api/security/mobile/auth/login', {
      db,
      username,
      login: username,
      password,
    });

    if (res.data?.success && res.data?.data) {
      const data = res.data.data;
      sessionId = data.session_id;
      profileData = {
        uid: data.uid,
        name: data.name,
        role: data.role,
        employee_id: data.employee_id ?? null,
      };
    }
  } catch (restErr: any) {
    console.warn('REST mobile login notice:', restErr?.message || 'Falling back to web authenticate');
  }

  // 2. Fallback to /web/session/authenticate if REST endpoint is unavailable or returned error
  if (!sessionId) {
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

    profileData.uid = result.uid;
    profileData.name = result.name;

    // Extract session_id from Set-Cookie header
    const setCookie = response.headers?.['set-cookie'] || response.headers?.['Set-Cookie'];
    if (setCookie) {
      const cookieStr = Array.isArray(setCookie) ? setCookie.join(';') : String(setCookie);
      const match = cookieStr.match(/session_id=([^;]+)/);
      if (match && match[1]) {
        sessionId = match[1];
      }
    }
    if (!sessionId && result.session_id) {
      sessionId = result.session_id;
    }
  }

  if (sessionId) {
    await setSessionId(sessionId);
  }

  // Resolve role from actual Odoo group membership if not set
  let role: 'supervisor' | 'manager' | 'owner' | 'guard' = profileData.role ?? 'guard';
  let employee_id: number | null = profileData.employee_id ?? null;

  if (!profileData.role) {
    try {
      const meResp = await client.get('/api/security/mobile/auth/me');
      if (meResp.data?.success && meResp.data?.data) {
        role = meResp.data.data.role ?? 'supervisor';
        if (meResp.data.data.employee_id) employee_id = meResp.data.data.employee_id;
      }
    } catch {
      const nameLower = (profileData.name || '').toLowerCase();
      const userLower = username.toLowerCase();
      const isOwner =
        nameLower.includes('owner') ||
        userLower.includes('owner') ||
        nameLower.includes('admin') ||
        userLower.includes('admin');
      const isManager = !isOwner && (nameLower.includes('manager') || userLower.includes('manager'));
      if (isOwner) role = 'owner';
      else if (isManager) role = 'manager';
    }
  }

  const profile: UserProfile = {
    uid: profileData.uid!,
    name: profileData.name!,
    username,
    db,
    role,
    employee_id,
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
    await SecureStore.deleteItemAsync('user_profile');
    await setSessionId(null);
  }
};
