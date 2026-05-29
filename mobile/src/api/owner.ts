import client from './client';

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
  monthly_payroll_trend: Array<{ month: string; cost: number }>;
  top_sites_by_attendance: Array<{
    site_id: number;
    site_name: string;
    client: string;
    total_records: number;
    present: number;
    attendance_rate: number;
  }>;
}

export const getOwnerKpis = async (selectedMonth?: string): Promise<OwnerKpisResponse> => {
  const params = selectedMonth ? { month: selectedMonth } : {};
  const response = await client.get('/api/security/mobile/owner/kpis', { params });
  if (response.data && response.data.success) {
    return response.data.data;
  }
  throw new Error(response.data?.error || 'Failed to fetch Owner KPIs');
};
