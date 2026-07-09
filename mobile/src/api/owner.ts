import client from './client';
import { cacheSet, cacheGetStale } from '../utils/apiCache';

// ─── Calendar types ────────────────────────────────────────────────────────
export interface CalendarDay {
  date: string;
  has_data: boolean;
  total: number;
  present: number;
  absent: number;
  awol: number;
  sites: number;
  rate: number;
}

export interface CalendarResponse {
  month: string;
  period_start: string;
  period_end: string;
  days: CalendarDay[];
}

// ─── Sites types ───────────────────────────────────────────────────────────
export interface SiteStats {
  total: number;
  present: number;
  absent: number;
  awol: number;
  late: number;
  rate: number;
}

export interface MarginData {
  revenue: number;
  payroll_cost: number;
  margin: number;
  margin_pct: number | null;
}

export interface OwnerSite {
  site_id: number;
  name: string;
  client: string | null;
  supervisor: string | null;
  today_state: 'draft' | 'confirmed' | 'no_batch';
  stats: SiteStats;
  margin: MarginData;
}

export interface SitesResponse {
  period: string;
  sites: OwnerSite[];
}

// ─── Guards types ──────────────────────────────────────────────────────────
export interface GuardStats {
  total: number;
  present: number;
  absent: number;
  awol: number;
  late: number;
  rate: number;
}

export interface OwnerGuard {
  id: number;
  name: string;
  grade: string | null;
  reliability_score: number | null;
  last_shift: string | null;
  stats: GuardStats;
}

export interface GuardsResponse {
  period_days: number;
  period_start: string;
  guards: OwnerGuard[];
}

export interface OwnerKpisResponse {
  period: string;
  period_start: string;
  period_end: string;
  attendance: {
    rate_percent: number;
    total_records: number;
    present: number;
    absent: number;
    awol: number;
    late: number;
  };
  total_guards: number;
  sites_active: number;
  open_incidents: number;
  payroll_cost_ytd: number;
  outstanding_invoices: number;
  monthly_payroll_trend: Array<{ month: string; month_key: string; cost: number }>;
  top_sites_by_attendance: Array<{
    site_id: number;
    site_name: string;
    client: string;
    total_records: number;
    present: number;
    attendance_rate: number;
  }>;
}

export const getOwnerKpis = async (selectedMonth?: string): Promise<OwnerKpisResponse & { _cached?: boolean; _cachedAt?: number }> => {
  const CACHE_KEY = `owner_kpis_${selectedMonth || 'current'}`;
  const params = selectedMonth ? { month: selectedMonth } : {};
  try {
    const response = await client.get('/api/security/mobile/owner/kpis', { params });
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch Owner KPIs');
  } catch (err) {
    const cached = await cacheGetStale<OwnerKpisResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true, _cachedAt: cached.cachedAt };
    throw err;
  }
};

export const getOwnerCalendar = async (month?: string): Promise<CalendarResponse & { _cached?: boolean }> => {
  const CACHE_KEY = `owner_calendar_${month || 'current'}`;
  const params = month ? { month } : {};
  try {
    const response = await client.get('/api/security/mobile/owner/calendar', { params });
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch calendar data');
  } catch (err) {
    const cached = await cacheGetStale<CalendarResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true };
    throw err;
  }
};

export const getOwnerSites = async (month?: string): Promise<SitesResponse & { _cached?: boolean }> => {
  const CACHE_KEY = `owner_sites_${month || 'current'}`;
  const params = month ? { month } : {};
  try {
    const response = await client.get('/api/security/mobile/owner/sites', { params });
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch sites data');
  } catch (err) {
    const cached = await cacheGetStale<SitesResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true };
    throw err;
  }
};

export const getOwnerGuards = async (days = 30): Promise<GuardsResponse & { _cached?: boolean }> => {
  const CACHE_KEY = `owner_guards_${days}`;
  try {
    const response = await client.get('/api/security/mobile/owner/guards', { params: { days } });
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch guards data');
  } catch (err) {
    const cached = await cacheGetStale<GuardsResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true };
    throw err;
  }
};

// ─── Site detail types ─────────────────────────────────────────────────────
export interface RosterEntry {
  guard_id: number | null;
  guard_name: string;
  grade: string | null;
  post: string | null;
  shift: string | null;
  presence: 'present' | 'absent' | 'awol' | 'not_marked';
  check_in: string | null;
  late_minutes: number;
}

export interface SiteDetailResponse {
  site: {
    id: number;
    name: string;
    code: string | null;
    location: string | null;
    note: string | null;
    client: { id: number; name: string; phone: string | null; mobile: string | null; email: string | null; street: string | null; city: string | null } | null;
    supervisor: { id: number; name: string; phone: string | null; mobile: string | null; email: string | null } | null;
  };
  today: {
    batch_id: number | null;
    batch_state: string;
    total: number;
    present: number;
    absent: number;
    awol: number;
    not_marked: number;
    rate: number;
    roster: RosterEntry[];
  };
  month_stats: { period: string; total: number; present: number; absent: number; awol: number; rate: number };
  trend: Array<{ date: string; total: number; present: number; rate: number; has_data: boolean }>;
  financials: {
    invoices_outstanding: number;
    invoices_count: number;
    aging: { current: number; days_30: number; days_60: number; days_90_plus: number };
    margin: MarginData | null;
  };
}

// ─── Guard detail types ────────────────────────────────────────────────────
export interface CertRecord {
  name: string | null;
  ref: string | null;
  issue_date: string | null;
  expiry_date: string | null;
  days_to_expiry: number | null;
  verified: boolean;
  is_expired: boolean;
  expiring_soon: boolean;
}

export interface GuardDetailResponse {
  guard: {
    id: number;
    name: string;
    grade: string | null;
    reliability_score: number;
    mobile_phone: string | null;
    work_phone: string | null;
    work_email: string | null;
    disqualified: boolean;
    certifications: CertRecord[];
    expiring_cert_count: number;
    attributes: string[];
  };
  today_assignment: {
    site_id: number | null;
    site_name: string | null;
    post: string | null;
    shift: string | null;
    presence: string;
    check_in: string | null;
  } | null;
  stats_30d: { total: number; present: number; absent: number; awol: number; late: number; rate: number };
  history: Array<{ date: string | null; site: string | null; post: string | null; shift: string | null; presence: string; late_minutes: number }>;
}

export const getOwnerSiteDetail = async (siteId: number): Promise<SiteDetailResponse & { _cached?: boolean }> => {
  const CACHE_KEY = `owner_site_detail_${siteId}`;
  try {
    const response = await client.get(`/api/security/mobile/owner/site/${siteId}`);
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch site detail');
  } catch (err) {
    const cached = await cacheGetStale<SiteDetailResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true };
    throw err;
  }
};

export const getOwnerGuardDetail = async (guardId: number): Promise<GuardDetailResponse & { _cached?: boolean }> => {
  const CACHE_KEY = `owner_guard_detail_${guardId}`;
  try {
    const response = await client.get(`/api/security/mobile/owner/guard/${guardId}`);
    if (response.data?.success) {
      await cacheSet(CACHE_KEY, response.data.data);
      return response.data.data;
    }
    throw new Error(response.data?.error || 'Failed to fetch guard profile');
  } catch (err) {
    const cached = await cacheGetStale<GuardDetailResponse>(CACHE_KEY);
    if (cached) return { ...cached.data, _cached: true };
    throw err;
  }
};
