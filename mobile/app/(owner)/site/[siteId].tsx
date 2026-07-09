import React, { useState, useEffect, useCallback } from 'react';
import {
  View, StyleSheet, ScrollView, RefreshControl,
  TouchableOpacity, Linking, Alert,
} from 'react-native';
import { Text, ActivityIndicator, Card, Chip } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getOwnerSiteDetail, SiteDetailResponse, RosterEntry, MarginData } from '../../../src/api/owner';
import MiniBarChart from '../../../src/components/MiniBarChart';
import { Theme } from '../../../src/theme';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';

function presenceColor(p: string): string {
  switch (p) {
    case 'present': return Theme.colors.present;
    case 'absent': return Theme.colors.absent;
    case 'awol': return Theme.colors.accentGold;
    default: return Theme.colors.placeholder;
  }
}

function presenceIcon(p: string): string {
  switch (p) {
    case 'present': return 'check-circle-outline';
    case 'absent': return 'close-circle-outline';
    case 'awol': return 'alert-circle-outline';
    default: return 'circle-outline';
  }
}

function batchStateLabel(s: string): { label: string; color: string } {
  switch (s) {
    case 'confirmed': return { label: 'Submitted', color: Theme.colors.present };
    case 'draft': return { label: 'In Progress', color: Theme.colors.accentGold };
    case 'captured': return { label: 'Captured', color: Theme.colors.primary };
    default: return { label: 'No Batch', color: Theme.colors.placeholder };
  }
}

function callNumber(phone: string | null, label: string) {
  if (!phone) { Alert.alert('No contact', `No ${label} number on file.`); return; }
  Linking.openURL(`tel:${phone}`);
}

function openWhatsApp(phone: string | null) {
  if (!phone) { Alert.alert('No contact', 'No mobile number on file.'); return; }
  const clean = phone.replace(/\D/g, '');
  Linking.openURL(`https://wa.me/${clean}`);
}

export default function OwnerSiteDetailScreen() {
  const { siteId } = useLocalSearchParams<{ siteId: string }>();
  const router = useRouter();
  const [data, setData] = useState<SiteDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [generatingReport, setGeneratingReport] = useState(false);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getOwnerSiteDetail(Number(siteId));
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load site details.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [siteId]);

  useEffect(() => { load(); }, [load]);

  const onRefresh = () => { setRefreshing(true); load(true); };

  const generateReport = useCallback(async () => {
    if (!data) return;
    setGeneratingReport(true);
    try {
      const { site, today, month_stats, financials } = data;
      const now = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
      const marginBlock = financials.margin
        ? `<tr><td>Month Revenue</td><td>N$${Math.round(financials.margin.revenue).toLocaleString()}</td></tr>
           <tr><td>Est. Payroll Cost</td><td>N$${Math.round(financials.margin.payroll_cost).toLocaleString()}</td></tr>
           <tr><td><strong>Margin</strong></td><td style="color:${financials.margin.margin >= 0 ? '#16a34a' : '#dc2626'}"><strong>N$${Math.round(financials.margin.margin).toLocaleString()}${financials.margin.margin_pct !== null ? ` (${financials.margin.margin_pct}%)` : ''}</strong></td></tr>`
        : '';
      const presentGuards = today.roster.filter(r => r.presence === 'present');
      const absentGuards = today.roster.filter(r => r.presence !== 'present' && r.presence !== 'not_marked');
      const html = `
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
  body { font-family: Arial, sans-serif; padding: 32px; color: #1e293b; font-size: 13px; }
  h1 { font-size: 22px; color: #1A56DB; margin-bottom: 4px; }
  h2 { font-size: 14px; color: #475569; margin-top: 24px; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
  .meta { color: #64748b; font-size: 11px; margin-bottom: 20px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  td, th { padding: 7px 10px; text-align: left; border-bottom: 1px solid #f1f5f9; }
  th { background: #f8fafc; font-weight: 600; font-size: 11px; text-transform: uppercase; color: #94a3b8; }
  .rate-big { font-size: 28px; font-weight: bold; color: #16a34a; }
  .badge-present { background: #dcfce7; color: #16a34a; padding: 2px 8px; border-radius: 4px; }
  .badge-absent { background: #fef9c3; color: #ca8a04; padding: 2px 8px; border-radius: 4px; }
  .badge-awol { background: #fee2e2; color: #dc2626; padding: 2px 8px; border-radius: 4px; }
  .footer { margin-top: 40px; font-size: 10px; color: #94a3b8; text-align: center; }
</style></head><body>
<h1>${site.name}</h1>
<div class="meta">
  ${site.client ? `Client: ${site.client.name} &nbsp;|&nbsp; ` : ''}
  ${site.supervisor ? `Supervisor: ${site.supervisor.name} &nbsp;|&nbsp; ` : ''}
  ${site.location || ''}
</div>
<p class="meta">Report generated: ${now} &nbsp;|&nbsp; Period: ${month_stats.period}</p>

<h2>Month Attendance — ${month_stats.period}</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total Shifts</td><td>${month_stats.total}</td></tr>
  <tr><td>Present</td><td>${month_stats.present}</td></tr>
  <tr><td>Absent</td><td>${month_stats.absent}</td></tr>
  <tr><td>AWOL</td><td>${month_stats.awol}</td></tr>
  <tr><td><strong>Attendance Rate</strong></td><td><strong>${month_stats.rate}%</strong></td></tr>
</table>

<h2>Today's Roster</h2>
<table>
  <tr><th>Guard</th><th>Grade</th><th>Post</th><th>Status</th><th>Check-in</th></tr>
  ${today.roster.map(r => `
  <tr>
    <td>${r.guard_name}</td>
    <td>${r.grade || '—'}</td>
    <td>${r.post || '—'}</td>
    <td><span class="badge-${r.presence === 'present' ? 'present' : r.presence === 'awol' ? 'awol' : 'absent'}">${r.presence.replace('_', ' ')}</span></td>
    <td>${r.check_in || '—'}</td>
  </tr>`).join('')}
</table>

<h2>Financial Summary</h2>
<table>
  <tr><th>Item</th><th>Amount</th></tr>
  <tr><td>Outstanding Invoices</td><td>N$${Math.round(financials.invoices_outstanding).toLocaleString()} (${financials.invoices_count} inv.)</td></tr>
  ${marginBlock}
</table>

<div class="footer">Generated by DeployGuard &copy; ${new Date().getFullYear()} — Confidential</div>
</body></html>`;

      const { uri } = await Print.printToFileAsync({ html, base64: false });
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(uri, {
          mimeType: 'application/pdf',
          dialogTitle: `${site.name} — ${month_stats.period} Report`,
          UTI: 'com.adobe.pdf',
        });
      } else {
        Alert.alert('Report Ready', `PDF saved to: ${uri}`);
      }
    } catch (err: any) {
      Alert.alert('Report Error', err.message || 'Could not generate report.');
    } finally {
      setGeneratingReport(false);
    }
  }, [data]);

  if (loading) {
    return <View style={styles.loader}><ActivityIndicator size="large" color={Theme.colors.primary} /></View>;
  }

  if (errorMsg || !data) {
    return (
      <View style={styles.errorBox}>
        <MaterialCommunityIcons name="alert-circle-outline" size={40} color={Theme.colors.absent} />
        <Text style={styles.errorText}>{errorMsg || 'No data available.'}</Text>
      </View>
    );
  }

  const { site, today, month_stats, trend, financials } = data;
  const batchBadge = batchStateLabel(today.batch_state);
  const sup = site.supervisor;

  // Build trend chart data — last 14 days for readability
  const trendData = trend.slice(-14).map(d => ({
    label: new Date(d.date + 'T00:00:00').getDate().toString(),
    value: d.rate,
  }));

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scroll}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
    >
      {/* ── Site header ─────────────────────────────────────────────── */}
      <Card style={styles.headerCard}>
        <Card.Content>
          <View style={styles.headerTop}>
            <View style={styles.headerLeft}>
              <Text style={styles.siteName}>{site.name}</Text>
              {site.client && <Text style={styles.clientName}>{site.client.name}</Text>}
              {site.location && (
                <View style={styles.locationRow}>
                  <MaterialCommunityIcons name="map-marker-outline" size={13} color={Theme.colors.placeholder} />
                  <Text style={styles.locationText}>{site.location}</Text>
                </View>
              )}
            </View>
            <View style={[styles.stateBadge, { backgroundColor: `${batchBadge.color}18`, borderColor: batchBadge.color }]}>
              <Text style={[styles.stateLabel, { color: batchBadge.color }]}>{batchBadge.label}</Text>
            </View>
          </View>

          {/* Quick action buttons */}
          {sup && (
            <View style={styles.actionRow}>
              <TouchableOpacity
                style={styles.actionBtn}
                onPress={() => callNumber(sup.mobile || sup.phone, 'supervisor')}
              >
                <MaterialCommunityIcons name="phone-outline" size={18} color={Theme.colors.primary} />
                <Text style={styles.actionLabel}>{sup.name}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionBtn, { borderColor: '#25D366' }]}
                onPress={() => openWhatsApp(sup.mobile || sup.phone)}
              >
                <MaterialCommunityIcons name="whatsapp" size={18} color="#25D366" />
                <Text style={[styles.actionLabel, { color: '#25D366' }]}>WhatsApp</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Report button */}
          <TouchableOpacity
            style={[styles.reportBtn, generatingReport && { opacity: 0.6 }]}
            onPress={generateReport}
            disabled={generatingReport}
            activeOpacity={0.75}
          >
            <MaterialCommunityIcons
              name={generatingReport ? 'loading' : 'file-pdf-box'}
              size={18}
              color="#fff"
            />
            <Text style={styles.reportBtnLabel}>
              {generatingReport ? 'Generating…' : 'Generate & Share Report'}
            </Text>
          </TouchableOpacity>
        </Card.Content>
      </Card>

      {/* ── Today's snapshot ────────────────────────────────────────── */}
      <Text style={styles.sectionTitle}>Today's Snapshot</Text>
      <View style={styles.statsRow}>
        {[
          { label: 'Total', value: today.total, color: Theme.colors.text },
          { label: 'Present', value: today.present, color: Theme.colors.present },
          { label: 'Absent', value: today.absent, color: Theme.colors.absent },
          { label: 'AWOL', value: today.awol, color: Theme.colors.accentGold },
          { label: 'Unmarked', value: today.not_marked, color: Theme.colors.placeholder },
        ].map(({ label, value, color }) => (
          <Card key={label} style={styles.statCard}>
            <Card.Content style={styles.statContent}>
              <Text style={[styles.statNum, { color }]}>{value}</Text>
              <Text style={styles.statLabel}>{label}</Text>
            </Card.Content>
          </Card>
        ))}
      </View>

      {/* ── Live roster ─────────────────────────────────────────────── */}
      {today.roster.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Live Roster</Text>
          {today.roster.map((entry, i) => (
            <RosterRow
              key={i}
              entry={entry}
              onGuardPress={() => entry.guard_id && router.push(`/(owner)/guard/${entry.guard_id}`)}
            />
          ))}
        </>
      )}

      {/* ── Month stats ─────────────────────────────────────────────── */}
      <Text style={styles.sectionTitle}>This Month — {month_stats.period}</Text>
      <Card style={styles.monthCard}>
        <Card.Content>
          <View style={styles.monthRow}>
            <View style={styles.monthRate}>
              <Text style={[styles.monthRateNum, {
                color: month_stats.rate >= 90 ? Theme.colors.present
                  : month_stats.rate >= 70 ? Theme.colors.accentGold
                  : Theme.colors.absent
              }]}>{month_stats.rate}%</Text>
              <Text style={styles.monthRateLabel}>Attendance Rate</Text>
            </View>
            <View style={styles.monthDivider} />
            <View style={styles.monthBreakdown}>
              {[
                { label: 'Present', value: month_stats.present, color: Theme.colors.present },
                { label: 'Absent', value: month_stats.absent, color: Theme.colors.absent },
                { label: 'AWOL', value: month_stats.awol, color: Theme.colors.accentGold },
              ].map(({ label, value, color }) => (
                <View key={label} style={styles.monthStat}>
                  <Text style={[styles.monthStatNum, { color }]}>{value}</Text>
                  <Text style={styles.monthStatLabel}>{label}</Text>
                </View>
              ))}
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* ── 30-day trend chart ──────────────────────────────────────── */}
      {trendData.some(d => d.value > 0) && (
        <>
          <Text style={styles.sectionTitle}>Attendance Trend (Last 14 Days)</Text>
          <Card style={styles.chartCard}>
            <Card.Content>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <MiniBarChart
                  data={trendData}
                  height={72}
                  barColor={Theme.colors.primary}
                />
              </ScrollView>
            </Card.Content>
          </Card>
        </>
      )}

      {/* ── Month Margin ─────────────────────────────────────────────── */}
      {financials.margin && (financials.margin.revenue > 0 || financials.margin.payroll_cost > 0) && (
        <>
          <Text style={styles.sectionTitle}>Monthly Margin</Text>
          <Card style={styles.finCard}>
            <Card.Content>
              <View style={styles.marginGrid}>
                <MarginBlock
                  label="Revenue"
                  value={financials.margin.revenue}
                  color={Theme.colors.accentCyan}
                  icon="cash-multiple"
                />
                <MarginBlock
                  label="Payroll Cost"
                  value={financials.margin.payroll_cost}
                  color={Theme.colors.absent}
                  icon="account-group-outline"
                />
                <MarginBlock
                  label="Margin"
                  value={financials.margin.margin}
                  color={financials.margin.margin >= 0 ? Theme.colors.present : Theme.colors.absent}
                  icon="trending-up"
                  suffix={financials.margin.margin_pct !== null ? ` (${financials.margin.margin_pct}%)` : ''}
                />
              </View>
              {financials.margin.revenue > 0 && (
                <View style={styles.marginBarOuter}>
                  <View style={[styles.marginBarFill, {
                    width: `${Math.min(100, Math.max(0, (financials.margin.payroll_cost / financials.margin.revenue) * 100))}%`,
                    backgroundColor: Theme.colors.absent,
                  }]} />
                </View>
              )}
              {financials.margin.revenue > 0 && (
                <Text style={styles.marginBarHint}>
                  Cost is {Math.round((financials.margin.payroll_cost / financials.margin.revenue) * 100)}% of revenue
                </Text>
              )}
            </Card.Content>
          </Card>
        </>
      )}

      {/* ── Financial / Invoice aging ────────────────────────────────── */}
      {financials.invoices_count > 0 && (
        <>
          <Text style={styles.sectionTitle}>Outstanding Invoices</Text>
          <Card style={styles.finCard}>
            <Card.Content>
              <View style={styles.finHeader}>
                <View>
                  <Text style={styles.finTotal}>
                    N${financials.invoices_outstanding.toLocaleString()}
                  </Text>
                  <Text style={styles.finSubtitle}>
                    {financials.invoices_count} invoice{financials.invoices_count !== 1 ? 's' : ''} outstanding
                  </Text>
                </View>
                <MaterialCommunityIcons name="file-document-outline" size={32} color={Theme.colors.accentGold} />
              </View>
              <View style={styles.agingRow}>
                {[
                  { label: 'Current', value: financials.aging.current, color: Theme.colors.present },
                  { label: '1–30d', value: financials.aging.days_30, color: Theme.colors.accentGold },
                  { label: '31–60d', value: financials.aging.days_60, color: Theme.colors.absent },
                  { label: '60d+', value: financials.aging.days_90_plus, color: '#7C3AED' },
                ].filter(a => a.value > 0).map(({ label, value, color }) => (
                  <View key={label} style={styles.agingItem}>
                    <View style={[styles.agingBar, { backgroundColor: color }]} />
                    <Text style={[styles.agingAmt, { color }]}>N${Math.round(value).toLocaleString()}</Text>
                    <Text style={styles.agingLabel}>{label}</Text>
                  </View>
                ))}
              </View>
            </Card.Content>
          </Card>
        </>
      )}
    </ScrollView>
  );
}

function MarginBlock({ label, value, color, icon, suffix = '' }: {
  label: string; value: number; color: string; icon: string; suffix?: string;
}) {
  return (
    <View style={styles.marginBlock}>
      <MaterialCommunityIcons name={icon as any} size={16} color={color} />
      <Text style={styles.marginBlockLabel}>{label}</Text>
      <Text style={[styles.marginBlockVal, { color }]}>
        N${Math.round(Math.abs(value)).toLocaleString()}{suffix}
      </Text>
    </View>
  );
}

function RosterRow({ entry, onGuardPress }: { entry: RosterEntry; onGuardPress: () => void }) {
  const color = presenceColor(entry.presence);
  const icon = presenceIcon(entry.presence);
  return (
    <TouchableOpacity style={styles.rosterRow} onPress={onGuardPress} activeOpacity={0.7}>
      <MaterialCommunityIcons name={icon as any} size={20} color={color} />
      <View style={styles.rosterInfo}>
        <Text style={styles.rosterName}>{entry.guard_name}</Text>
        <Text style={styles.rosterMeta}>
          {[entry.grade, entry.post, entry.shift].filter(Boolean).join(' · ')}
        </Text>
      </View>
      <View style={styles.rosterRight}>
        {entry.check_in && <Text style={styles.checkIn}>{entry.check_in}</Text>}
        {entry.late_minutes > 0 && (
          <Text style={styles.lateText}>{entry.late_minutes}min late</Text>
        )}
        <MaterialCommunityIcons name="chevron-right" size={16} color={Theme.colors.placeholder} />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  scroll: { padding: 16, paddingBottom: 40 },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorBox: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, padding: 32 },
  errorText: { color: Theme.colors.absent, textAlign: 'center' },

  headerCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 20,
    marginBottom: 20,
  },
  headerTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  headerLeft: { flex: 1, marginRight: 12 },
  siteName: { fontSize: 20, fontWeight: 'bold', color: Theme.colors.text },
  clientName: { fontSize: 13, color: Theme.colors.placeholder, marginTop: 4 },
  locationRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6 },
  locationText: { fontSize: 12, color: Theme.colors.placeholder },
  stateBadge: {
    borderWidth: 1.5,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  stateLabel: { fontSize: 10, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  actionRow: { flexDirection: 'row', gap: 10 },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1.5,
    borderColor: Theme.colors.primary,
    borderRadius: 12,
    paddingVertical: 10,
  },
  actionLabel: { fontSize: 13, fontWeight: '600', color: Theme.colors.primary },

  sectionTitle: {
    fontSize: 11,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
    marginTop: 4,
  },

  statsRow: { flexDirection: 'row', gap: 8, marginBottom: 20, flexWrap: 'wrap' },
  statCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 14,
    flex: 1,
    minWidth: 56,
  },
  statContent: { alignItems: 'center', paddingVertical: 10, paddingHorizontal: 4 },
  statNum: { fontSize: 18, fontWeight: 'bold' },
  statLabel: { fontSize: 9, color: Theme.colors.placeholder, textTransform: 'uppercase', marginTop: 2 },

  rosterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginBottom: 8,
    gap: 12,
  },
  rosterInfo: { flex: 1 },
  rosterName: { fontSize: 14, fontWeight: '600', color: Theme.colors.text },
  rosterMeta: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  rosterRight: { alignItems: 'flex-end', gap: 2 },
  checkIn: { fontSize: 12, fontWeight: '600', color: Theme.colors.text },
  lateText: { fontSize: 10, color: Theme.colors.absent },

  monthCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 18,
    marginBottom: 20,
  },
  monthRow: { flexDirection: 'row', alignItems: 'center' },
  monthRate: { alignItems: 'center', flex: 1 },
  monthRateNum: { fontSize: 32, fontWeight: 'bold', letterSpacing: -1 },
  monthRateLabel: { fontSize: 10, color: Theme.colors.placeholder, textTransform: 'uppercase', marginTop: 2 },
  monthDivider: { width: 1, height: 48, backgroundColor: Theme.colors.border, marginHorizontal: 16 },
  monthBreakdown: { flexDirection: 'row', gap: 16, flex: 2, justifyContent: 'space-around' },
  monthStat: { alignItems: 'center' },
  monthStatNum: { fontSize: 18, fontWeight: 'bold' },
  monthStatLabel: { fontSize: 10, color: Theme.colors.placeholder, marginTop: 2 },

  chartCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 18,
    marginBottom: 20,
  },

  finCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 18,
    marginBottom: 20,
  },
  finHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  finTotal: { fontSize: 22, fontWeight: 'bold', color: Theme.colors.text },
  finSubtitle: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  agingRow: { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  agingItem: { alignItems: 'center', gap: 4 },
  agingBar: { width: 40, height: 4, borderRadius: 2 },
  agingAmt: { fontSize: 12, fontWeight: 'bold' },
  agingLabel: { fontSize: 9, color: Theme.colors.placeholder, textTransform: 'uppercase' },
  marginGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  marginBlock: { flex: 1, alignItems: 'center', gap: 4 },
  marginBlockLabel: { fontSize: 9, color: Theme.colors.placeholder, textTransform: 'uppercase' },
  marginBlockVal: { fontSize: 12, fontWeight: 'bold', textAlign: 'center' },
  marginBarOuter: {
    height: 6,
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 4,
  },
  marginBarFill: { height: 6, borderRadius: 3 },
  marginBarHint: { fontSize: 10, color: Theme.colors.placeholder, textAlign: 'center' },
  reportBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: Theme.colors.primary,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    marginTop: 12,
  },
  reportBtnLabel: { color: '#fff', fontWeight: '700', fontSize: 13 },
});
