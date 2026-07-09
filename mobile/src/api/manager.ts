import client from './client';
import { cacheSet, cacheGetStale } from '../utils/apiCache';

export interface SiteSummary {
  site_id: number;
  site_name: string;
  client: string;
  supervisor: string | null;
  total_slots: number;
  present: number;
  absent: number;
  awol: number;
  late: number;
  not_marked: number;
  attendance_rate: number;
  batch_state: string;
  batch_id: number | null;
}

export interface ManagerDashboardResponse {
  date: string;
  overall: {
    total_slots: number;
    present: number;
    absent: number;
    awol: number;
    late: number;
    attendance_rate: number;
  };
  sites: SiteSummary[];
}

export interface SiteDetailResponse {
  date: string;
  site: { id: number; name: string; client: string };
  batch_id: number | null;
  batch_state: string;
  supervisor: string | null;
  roster: Array<{
    record_id: number | null;
    slot_id: number | null;
    guard: { id: number; name: string; grade: string | null };
    post: string | null;
    shift: string | null;
    manual_presence: 'present' | 'absent' | 'awol' | 'not_marked';
    check_in: string | null;
    check_out: string | null;
    late_minutes: number;
    overtime_hours: number;
    overtime_approved: boolean;
  }>;
  overtime_pending: Array<{
    record_id: number;
    guard: { id: number; name: string; grade: string | null };
    post: string | null;
    shift: string | null;
    manual_presence: string;
    check_in: string | null;
    check_out: string | null;
    late_minutes: number;
    overtime_hours: number;
    overtime_approved: boolean;
  }>;
}

export interface OvertimeRecord {
  record_id: number;
  guard: { id: number; name: string; grade: string | null };
  site_name: string | null;
  post: string | null;
  shift: string | null;
  hours: number;
  date: string | null;
}

export const getManagerDashboard = async (selectedDate?: string): Promise<ManagerDashboardResponse & { _cached?: boolean; _cachedAt?: number }> => {
  const CACHE_KEY = `manager_dashboard_${selectedDate || 'today'}`;
  const params = selectedDate ? { date: selectedDate } : {};
  try {
    const response = await client.get('/api/security/mobile/manager/dashboard', { params });
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch manager dashboard');
  } catch (err) {
    const cached = await cacheGetStale<ManagerDashboardResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true, _cachedAt: cached.cachedAt };
    throw err;
  }
};

export const getSiteDetails = async (siteId: number, selectedDate?: string): Promise<SiteDetailResponse & { _cached?: boolean; _cachedAt?: number }> => {
  const CACHE_KEY = `manager_site_${siteId}_${selectedDate || 'today'}`;
  const params = selectedDate ? { date: selectedDate } : {};
  try {
    const response = await client.get(`/api/security/mobile/manager/site/${siteId}`, { params });
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch site details');
  } catch (err) {
    const cached = await cacheGetStale<SiteDetailResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true, _cachedAt: cached.cachedAt };
    throw err;
  }
};

export const getOvertimeList = async (): Promise<OvertimeRecord[]> => {
  const response = await client.get('/api/security/mobile/manager/overtime');
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to fetch overtime list');
};

export interface LeaveRequest {
  id: number;
  employee: { id: number; name: string; grade: string | null };
  leave_type: string | null;
  date_from: string;
  date_to: string;
  requested_days: number;
  state: string;
  balance_days: number | null;
}

export const getLeaveRequests = async (): Promise<LeaveRequest[]> => {
  const response = await client.get('/api/security/mobile/manager/leave-requests');
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to fetch leave requests');
};

export const leaveAction = async (
  reqId: number,
  action: 'approve' | 'refuse'
): Promise<{ id: number; employee: string; new_state: string }> => {
  const response = await client.post(`/api/security/mobile/manager/leave-requests/${reqId}/action`, { action });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to process leave request');
};

export interface UnassignedSlotEntry {
  slot_id: number;
  shift_date: string;
  post: string | null;
  shift: string | null;
}

export interface UnassignedSiteSummary {
  site_id: number;
  site_name: string;
  count: number;
  slots: UnassignedSlotEntry[];
}

export interface UnassignedSlotsResponse {
  total: number;
  sites: UnassignedSiteSummary[];
}

export const getUnassignedSlots = async (): Promise<UnassignedSlotsResponse> => {
  const response = await client.get('/api/security/mobile/manager/unassigned-slots');
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to fetch unassigned slots');
};

export interface PerformanceFlag {
  type: 'late' | 'awol' | 'ot';
  label: string;
}

export interface FlaggedGuard {
  id: number;
  name: string;
  grade: string | null;
  late_count: number;
  awol_count: number;
  ot_hours: number;
  flags: PerformanceFlag[];
}

export interface GuardPerformanceResponse {
  total_flagged: number;
  guards: FlaggedGuard[];
}

export const getGuardPerformance = async (): Promise<GuardPerformanceResponse> => {
  const response = await client.get('/api/security/mobile/manager/guard-performance');
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to fetch guard performance');
};

export const initiateGuardReview = async (
  employeeId: number,
  note: string
): Promise<{ employee_id: number; employee_name: string }> => {
  const response = await client.post('/api/security/mobile/manager/guard/review', {
    employee_id: employeeId,
    note,
  });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to initiate review');
};

export interface OtSiteSummary {
  site_id: number;
  site_name: string;
  ot_hours: number;
}

export interface OtSummaryResponse {
  month: string;
  days_elapsed: number;
  days_in_month: number;
  total_ot_hours: number;
  projected_ot_hours: number;
  sites: OtSiteSummary[];
}

export const getOtSummary = async (): Promise<OtSummaryResponse> => {
  const response = await client.get('/api/security/mobile/manager/ot-summary');
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to fetch OT summary');
};

export const approveOvertime = async (
  recordId: number,
  approved: boolean,
  note?: string
): Promise<{ record_id: number; overtime_approved: boolean }> => {
  const response = await client.post('/api/security/mobile/manager/overtime/approve', {
    record_id: recordId,
    approved,
    note,
  });
  if (response.data?.success) return response.data.data;
  throw new Error(response.data?.error || 'Failed to approve overtime');
};
