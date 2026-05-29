import client from './client';

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

export const getManagerDashboard = async (selectedDate?: string): Promise<ManagerDashboardResponse> => {
  const params = selectedDate ? { date: selectedDate } : {};
  const response = await client.get('/api/security/mobile/manager/dashboard', { params });
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to fetch manager dashboard');
};

export const getSiteDetails = async (siteId: number, selectedDate?: string): Promise<SiteDetailResponse> => {
  const params = selectedDate ? { date: selectedDate } : {};
  const response = await client.get(`/api/security/mobile/manager/site/${siteId}`, { params });
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to fetch site details');
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
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to approve overtime');
};
