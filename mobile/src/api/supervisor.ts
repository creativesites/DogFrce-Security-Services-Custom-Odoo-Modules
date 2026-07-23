import client, { isOffline } from './client';
import { cacheSet, cacheGetStale } from '../utils/apiCache';

export interface GuardInfo {
  id: number;
  name: string;
  grade: string | null;
}

export interface AttendanceRecord {
  record_id: number;
  slot_id: number | null;
  guard: GuardInfo;
  post: string | null;
  post_id: number | null;
  shift: string | null;
  shift_template_id: number | null;
  shift_start: number | null;
  shift_end: number | null;
  status: string;
  manual_presence: 'present' | 'absent' | 'awol' | 'not_marked';
  check_in: string | null;
  check_out: string | null;
  late_minutes: number;
  overtime_hours: number;
  override_reason: string | null;
}

export interface SiteDaySummary {
  site_id: number;
  site_name: string;
  client: string | null;
  supervisor: string | null;
  batch_id: number | null;
  batch_state: string;
  date: string;
  total: number;
  present: number;
  absent: number;
  awol: number;
  not_marked: number;
  attendance_rate: number;
  has_batch: boolean;
}

export interface AllSitesResponse {
  date: string;
  sites: SiteDaySummary[];
}

export interface PostingSheetBatch {
  batch_id: number;
  batch_state: 'draft' | 'captured' | 'confirmed' | 'cancelled';
  date: string;
  site: { id: number; name: string } | null;
  client: { id: number; name: string } | null;
  slots: AttendanceRecord[];
}

export interface RosterSlotFallback {
  slot_id: number;
  guard: GuardInfo;
  post: string;
  site: { id: number; name: string } | null;
  shift: string;
  shift_start: number;
  shift_end: number;
  state: string;
}

export interface SitePostingSheetResponse {
  date: string;
  has_batch?: boolean;
  roster_slots?: RosterSlotFallback[];
  batch_id?: number;
  batch_state?: 'draft' | 'captured' | 'confirmed' | 'cancelled';
  site?: { id: number; name: string } | null;
  client?: { id: number; name: string } | null;
  slots?: AttendanceRecord[];
}

/** Returns all-sites summary (no site_id param). */
export const getAllSites = async (): Promise<AllSitesResponse & { _cached?: boolean; _cachedAt?: number }> => {
  const CACHE_KEY = 'supervisor_all_sites';
  try {
    const response = await client.get('/api/security/mobile/supervisor/today');
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch sites');
  } catch (err) {
    const cached = await cacheGetStale<AllSitesResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true, _cachedAt: cached.cachedAt };
    throw err;
  }
};

/** Returns the posting sheet for one specific site. */
export const getSitePostingSheet = async (siteId: number): Promise<SitePostingSheetResponse & { _cached?: boolean; _cachedAt?: number }> => {
  const CACHE_KEY = `supervisor_sheet_${siteId}`;
  try {
    const response = await client.get('/api/security/mobile/supervisor/today', {
      params: { site_id: siteId },
    });
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch posting sheet');
  } catch (err) {
    const cached = await cacheGetStale<SitePostingSheetResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true, _cachedAt: cached.cachedAt };
    throw err;
  }
};

export const markPresence = async (
  recordId: number,
  presence: 'present' | 'absent' | 'awol' | 'not_marked',
  overrideReason?: string,
  checkIn?: string,
  checkOut?: string
): Promise<AttendanceRecord> => {
  const response = await client.post('/api/security/mobile/supervisor/mark', {
    record_id: recordId,
    manual_presence: presence,
    override_reason: overrideReason,
    check_in: checkIn,
    check_out: checkOut,
  });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to mark presence');
};

export const quickCheckIn = async (
  recordId: number,
  action: 'check_in' | 'check_out',
  location?: { latitude: number; longitude: number; accuracy?: number }
): Promise<AttendanceRecord> => {
  const response = await client.post('/api/security/mobile/supervisor/checkin', {
    record_id: recordId,
    action,
    latitude: location?.latitude,
    longitude: location?.longitude,
    accuracy: location?.accuracy,
  });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to capture timestamp');
};

export const submitBatch = async (batchId: number): Promise<{ batch_id: number; new_state: string }> => {
  const response = await client.post('/api/security/mobile/supervisor/batch/submit', {
    batch_id: batchId,
  });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to submit batch');
};

export interface HistoryBatch {
  batch_id: number;
  date: string;
  site: { id: number; name: string } | null;
  state: string;
  summary: {
    total: number;
    present: number;
    late: number;
    absent: number;
    awol: number;
    attendance_rate: number;
  };
}

export interface HistoryResponse {
  batches: HistoryBatch[];
  pagination: { limit: number; offset: number; total: number };
}

// ── Assign guard ─────────────────────────────────────────────────────────────

export interface AssignableGuard {
  id: number;
  name: string;
  grade: string | null;
}

export interface AssignablePost {
  id: number;
  name: string;
}

export interface AssignableShift {
  id: number;
  name: string;
  start_hour: number;
  end_hour: number;
  duration_hours: number;
}

export interface AssignableData {
  site_id: number;
  site_name: string;
  guards: AssignableGuard[];
  posts: AssignablePost[];
  shifts: AssignableShift[];
  has_batch: boolean;
  batch_state: string | null;
}

export interface AssignResult {
  record_id: number;
  batch_id: number;
  slot_id: number;
  guard: { id: number; name: string };
  post: string;
  shift: string;
  manual_presence: string;
  check_in: string | null;
}

export const getAssignableData = async (siteId: number): Promise<AssignableData> => {
  const response = await client.get(`/api/security/mobile/supervisor/site/${siteId}/assignable`);
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to load assignment data');
};

export const assignGuard = async (
  siteId: number,
  employeeId: number,
  postId: number,
  shiftTemplateId: number,
  markPresent: boolean
): Promise<AssignResult> => {
  const response = await client.post(
    `/api/security/mobile/supervisor/site/${siteId}/assign`,
    { employee_id: employeeId, post_id: postId, shift_template_id: shiftTemplateId, mark_present: markPresent }
  );
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to assign guard');
};

export interface GuardAttendanceDay {
  date: string;
  presence: 'present' | 'absent' | 'awol' | 'not_marked' | 'no_shift';
}

export interface GuardActiveLeave {
  leave_type: string;
  date_from: string;
  date_to: string;
  requested_days: number;
}

export interface GuardProfileData {
  id: number;
  name: string;
  grade: string | null;
  reliability_score: number | null;
  mobile_phone: string | null;
  site: string | null;
  attendance_7d: GuardAttendanceDay[];
  open_incidents: number;
  active_leave: GuardActiveLeave | null;
}

export const getGuardProfile = async (guardId: number): Promise<GuardProfileData> => {
  const response = await client.get(`/api/security/mobile/supervisor/guard/${guardId}/profile`);
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to load guard profile');
};

export const bulkMarkPresent = async (siteId: number): Promise<{ updated: number; batch_id: number }> => {
  const response = await client.post(`/api/security/mobile/supervisor/site/${siteId}/bulk-mark`, {});
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to bulk-mark guards');
};

export interface IncidentType {
  id: number;
  name: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  deduction_amount: number;
}

export interface IncidentLogResult {
  incident_id: number;
  guard: string;
  incident_type: string;
  severity: string;
  date: string;
  state: string;
}

export const getIncidentTypes = async (): Promise<IncidentType[]> => {
  const response = await client.get('/api/security/mobile/supervisor/incident-types');
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to load incident types');
};

export const logIncident = async (
  employeeId: number,
  incidentTypeId: number,
  note?: string,
  photoBase64?: string,
  location?: { latitude: number; longitude: number }
): Promise<IncidentLogResult> => {
  const response = await client.post('/api/security/mobile/supervisor/incident', {
    employee_id: employeeId,
    incident_type_id: incidentTypeId,
    note: note || '',
    photo_base64: photoBase64,
    latitude: location?.latitude,
    longitude: location?.longitude,
  });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to log incident');
};

export interface ReassignResult {
  released_guard: string;
  new_record_id: number;
  batch_id: number;
  slot_id: number;
  guard: { id: number; name: string };
  post: string;
  shift: string;
  manual_presence: string;
  check_in: string | null;
}

export const reassignGuard = async (
  siteId: number,
  recordId: number,
  employeeId: number,
  postId: number,
  shiftTemplateId: number,
  markPresent = true
): Promise<ReassignResult> => {
  const response = await client.post(
    `/api/security/mobile/supervisor/site/${siteId}/reassign`,
    {
      record_id: recordId,
      employee_id: employeeId,
      post_id: postId,
      shift_template_id: shiftTemplateId,
      mark_present: markPresent,
    }
  );
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to reassign guard');
};

export const getHistory = async (limit = 20, offset = 0, siteId?: number): Promise<HistoryResponse> => {
  const params: Record<string, any> = { limit, offset };
  if (siteId) params.site_id = siteId;
  const response = await client.get('/api/security/mobile/supervisor/history', { params });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to fetch history');
};
