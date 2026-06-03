import client from './client';

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
  shift: string | null;
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

export interface TodayResponse {
  date: string;
  has_batch?: boolean;
  roster_slots?: RosterSlotFallback[];
  // If batch exists, it mirrors PostingSheetBatch directly
  batch_id?: number;
  batch_state?: 'draft' | 'captured' | 'confirmed' | 'cancelled';
  site?: { id: number; name: string } | null;
  slots?: AttendanceRecord[];
}

export const getTodayPostingSheet = async (): Promise<TodayResponse> => {
  const response = await client.get('/api/security/mobile/supervisor/today');
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to fetch posting sheet');
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
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to mark presence');
};

export const quickCheckIn = async (recordId: number, action: 'check_in' | 'check_out'): Promise<AttendanceRecord> => {
  const response = await client.post('/api/security/mobile/supervisor/checkin', {
    record_id: recordId,
    action,
  });
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to capture timestamp');
};

export const submitBatch = async (batchId: number): Promise<{ batch_id: number; new_state: string }> => {
  const response = await client.post('/api/security/mobile/supervisor/batch/submit', {
    batch_id: batchId,
  });
  if (response.data && response.data.success) {
    return response.data.data;
  }
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

export const getHistory = async (limit = 20, offset = 0): Promise<HistoryResponse> => {
  const response = await client.get('/api/security/mobile/supervisor/history', {
    params: { limit, offset },
  });
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to fetch history');
};
