import client from './client';

export interface GuardProfileInfo {
  id: number;
  name: string;
  grade: string;
  reliability_score: number;
}

export interface GuardSiteInfo {
  id: number;
  name: string;
}

export interface GuardShiftInfo {
  id: number;
  name: string;
  start_hour: number;
  end_hour: number;
}

export interface GuardSupervisorInfo {
  id: number;
  name: string;
  phone: string | null;
}

export interface GuardAttendanceStatus {
  record_id: number;
  status: 'present' | 'absent' | 'awol' | 'not_marked';
  check_in: string | null;
  check_out: string | null;
  late_minutes: number;
}

export interface GuardTodayData {
  guard: GuardProfileInfo;
  date: string;
  has_assignment: boolean;
  site: GuardSiteInfo | null;
  post: string | null;
  shift: GuardShiftInfo | null;
  supervisor: GuardSupervisorInfo | null;
  attendance: GuardAttendanceStatus | null;
}

export const getGuardToday = async (): Promise<GuardTodayData> => {
  const res = await client.get('/api/security/mobile/guard/today');
  if (res.data?.success) return res.data.data;
  throw new Error(res.data?.error || 'Failed to load shift details.');
};

export const guardCheckIn = async (
  action: 'check_in' | 'check_out',
  location?: { latitude: number; longitude: number; accuracy?: number },
  photoBase64?: string
): Promise<{ record_id: number; action: string; manual_presence: string; check_in: string | null; check_out: string | null }> => {
  const res = await client.post('/api/security/mobile/guard/checkin', {
    action,
    latitude: location?.latitude,
    longitude: location?.longitude,
    accuracy: location?.accuracy,
    photo_base64: photoBase64,
  });
  if (res.data?.success) return res.data.data;
  throw new Error(res.data?.error || 'Self check-in failed.');
};

export const guardLogPatrol = async (
  note: string,
  location?: { latitude: number; longitude: number },
  photoBase64?: string
): Promise<{ patrol_id: number; note: string; status: string }> => {
  const res = await client.post('/api/security/mobile/guard/patrol', {
    note,
    latitude: location?.latitude,
    longitude: location?.longitude,
    photo_base64: photoBase64,
  });
  if (res.data?.success) return res.data.data;
  throw new Error(res.data?.error || 'Failed to log patrol update.');
};

export const guardSendSOS = async (
  location?: { latitude: number; longitude: number },
  message?: string
): Promise<{ sos_id: number; status: string; message: string }> => {
  const res = await client.post('/api/security/mobile/guard/sos', {
    latitude: location?.latitude,
    longitude: location?.longitude,
    message,
  });
  if (res.data?.success) return res.data.data;
  throw new Error(res.data?.error || 'Failed to send panic alert.');
};

export interface GuardHistoryItem {
  record_id: number;
  date: string;
  site: string;
  post: string | null;
  shift: string | null;
  presence: string;
  check_in: string | null;
  check_out: string | null;
  late_minutes: number;
}

export interface GuardHistoryResponse {
  summary: {
    total_shifts: number;
    present: number;
    late: number;
    absent: number;
    attendance_rate: number;
  };
  history: GuardHistoryItem[];
}

export const getGuardHistory = async (): Promise<GuardHistoryResponse> => {
  const res = await client.get('/api/security/mobile/guard/history');
  if (res.data?.success) return res.data.data;
  throw new Error(res.data?.error || 'Failed to load guard history.');
};
