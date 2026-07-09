import React, { useState, useEffect, useCallback } from 'react';
import {
  View, StyleSheet, ScrollView, RefreshControl,
  TouchableOpacity, Linking,
} from 'react-native';
import { Text, ActivityIndicator, Card } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getOwnerGuardDetail, GuardDetailResponse, CertRecord } from '../../../src/api/owner';
import { Theme } from '../../../src/theme';

function reliabilityColor(score: number): string {
  if (score >= 85) return Theme.colors.present;
  if (score >= 65) return Theme.colors.accentGold;
  return Theme.colors.absent;
}

function presenceColor(p: string): string {
  switch (p) {
    case 'present': return Theme.colors.present;
    case 'absent': return Theme.colors.absent;
    case 'awol': return Theme.colors.accentGold;
    default: return Theme.colors.placeholder;
  }
}

function presenceLabel(p: string): string {
  switch (p) {
    case 'present': return 'Present';
    case 'absent': return 'Absent';
    case 'awol': return 'AWOL';
    default: return 'Unmarked';
  }
}

export default function OwnerGuardProfileScreen() {
  const { guardId } = useLocalSearchParams<{ guardId: string }>();
  const router = useRouter();
  const [data, setData] = useState<GuardDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getOwnerGuardDetail(Number(guardId));
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load guard profile.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [guardId]);

  useEffect(() => { load(); }, [load]);

  const onRefresh = () => { setRefreshing(true); load(true); };

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

  const { guard, today_assignment, stats_30d, history } = data;
  const relColor = reliabilityColor(guard.reliability_score);
  const hasContact = guard.mobile_phone || guard.work_phone;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scroll}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
    >
      {/* ── Guard header ────────────────────────────────────────────── */}
      <Card style={styles.headerCard}>
        <Card.Content>
          <View style={styles.headerRow}>
            <View style={[styles.avatar, { borderColor: relColor }]}>
              <MaterialCommunityIcons name="shield-account" size={32} color={relColor} />
            </View>
            <View style={styles.headerInfo}>
              <Text style={styles.guardName}>{guard.name}</Text>
              {guard.grade && <Text style={styles.gradeBadge}>{guard.grade}</Text>}
              {guard.disqualified && (
                <View style={styles.disqRow}>
                  <MaterialCommunityIcons name="alert" size={14} color={Theme.colors.absent} />
                  <Text style={styles.disqText}>Disqualified</Text>
                </View>
              )}
            </View>
            <View style={styles.scoreBlock}>
              <Text style={[styles.scoreNum, { color: relColor }]}>{guard.reliability_score}</Text>
              <Text style={styles.scoreLabel}>Reliability</Text>
              <View style={styles.scoreBar}>
                <View style={[styles.scoreFill, {
                  width: `${Math.min(100, guard.reliability_score)}%`,
                  backgroundColor: relColor,
                }]} />
              </View>
            </View>
          </View>

          {/* Attributes */}
          {guard.attributes.length > 0 && (
            <View style={styles.attrRow}>
              {guard.attributes.map((a) => (
                <View key={a} style={styles.attrChip}>
                  <Text style={styles.attrText}>{a}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Contact */}
          {hasContact && (
            <View style={styles.contactRow}>
              {guard.mobile_phone && (
                <TouchableOpacity
                  style={styles.contactBtn}
                  onPress={() => Linking.openURL(`tel:${guard.mobile_phone}`)}
                >
                  <MaterialCommunityIcons name="phone-outline" size={16} color={Theme.colors.primary} />
                  <Text style={styles.contactLabel}>Call</Text>
                </TouchableOpacity>
              )}
              {guard.mobile_phone && (
                <TouchableOpacity
                  style={[styles.contactBtn, { borderColor: '#25D366' }]}
                  onPress={() => {
                    const clean = guard.mobile_phone!.replace(/\D/g, '');
                    Linking.openURL(`https://wa.me/${clean}`);
                  }}
                >
                  <MaterialCommunityIcons name="whatsapp" size={16} color="#25D366" />
                  <Text style={[styles.contactLabel, { color: '#25D366' }]}>WhatsApp</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </Card.Content>
      </Card>

      {/* ── Today's assignment ──────────────────────────────────────── */}
      <Text style={styles.sectionTitle}>Today</Text>
      <Card style={styles.card}>
        <Card.Content>
          {today_assignment ? (
            <View style={styles.todayRow}>
              <View style={styles.todayLeft}>
                <TouchableOpacity
                  onPress={() => today_assignment.site_id && router.push(`/(owner)/site/${today_assignment.site_id}`)}
                >
                  <Text style={styles.todaySite}>{today_assignment.site_name ?? 'Unknown site'}</Text>
                </TouchableOpacity>
                <Text style={styles.todayMeta}>
                  {[today_assignment.post, today_assignment.shift].filter(Boolean).join(' · ')}
                </Text>
                {today_assignment.check_in && (
                  <Text style={styles.todayCheckIn}>Clocked in: {today_assignment.check_in}</Text>
                )}
              </View>
              <View style={[styles.presenceBadge, {
                backgroundColor: `${presenceColor(today_assignment.presence)}18`,
                borderColor: presenceColor(today_assignment.presence),
              }]}>
                <Text style={[styles.presenceText, { color: presenceColor(today_assignment.presence) }]}>
                  {presenceLabel(today_assignment.presence)}
                </Text>
              </View>
            </View>
          ) : (
            <View style={styles.notAssigned}>
              <MaterialCommunityIcons name="calendar-blank-outline" size={28} color={Theme.colors.placeholder} />
              <Text style={styles.notAssignedText}>Not scheduled today</Text>
            </View>
          )}
        </Card.Content>
      </Card>

      {/* ── 30-day stats ────────────────────────────────────────────── */}
      <Text style={styles.sectionTitle}>Last 30 Days</Text>
      <View style={styles.statsRow}>
        {[
          { label: 'Shifts', value: stats_30d.total, color: Theme.colors.text },
          { label: 'Present', value: stats_30d.present, color: Theme.colors.present },
          { label: 'Absent', value: stats_30d.absent, color: Theme.colors.absent },
          { label: 'AWOL', value: stats_30d.awol, color: Theme.colors.accentGold },
          { label: 'Late', value: stats_30d.late, color: Theme.colors.late },
        ].map(({ label, value, color }) => (
          <Card key={label} style={styles.statCard}>
            <Card.Content style={styles.statContent}>
              <Text style={[styles.statNum, { color }]}>{value}</Text>
              <Text style={styles.statLabel}>{label}</Text>
            </Card.Content>
          </Card>
        ))}
      </View>
      <Card style={styles.rateCard}>
        <Card.Content style={styles.rateContent}>
          <Text style={[styles.rateNum, { color: reliabilityColor(stats_30d.rate) }]}>
            {stats_30d.total > 0 ? `${stats_30d.rate}%` : '—'}
          </Text>
          <Text style={styles.rateLabel}>Attendance rate (30 days)</Text>
        </Card.Content>
      </Card>

      {/* ── Certifications ──────────────────────────────────────────── */}
      {guard.certifications.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>
            Certifications
            {guard.expiring_cert_count > 0 && (
              <Text style={styles.expWarn}> · {guard.expiring_cert_count} expiring</Text>
            )}
          </Text>
          {guard.certifications.map((cert, i) => (
            <CertRow key={i} cert={cert} />
          ))}
        </>
      )}

      {/* ── Recent shift history ─────────────────────────────────────── */}
      {history.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Recent Shifts</Text>
          {history.map((h, i) => (
            <View key={i} style={styles.historyRow}>
              <View style={styles.historyLeft}>
                <Text style={styles.historyDate}>
                  {h.date ? new Date(h.date + 'T00:00:00').toLocaleDateString('en-GB', {
                    weekday: 'short', day: 'numeric', month: 'short',
                  }) : '—'}
                </Text>
                <Text style={styles.historyMeta}>
                  {[h.site, h.post, h.shift].filter(Boolean).join(' · ')}
                </Text>
              </View>
              <View style={styles.historyRight}>
                <Text style={[styles.historyPresence, { color: presenceColor(h.presence) }]}>
                  {presenceLabel(h.presence)}
                </Text>
                {h.late_minutes > 0 && (
                  <Text style={styles.lateText}>{h.late_minutes}min late</Text>
                )}
              </View>
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}

function CertRow({ cert }: { cert: CertRecord }) {
  const isIssue = cert.is_expired || cert.expiring_soon;
  const iconColor = cert.is_expired ? Theme.colors.absent
    : cert.expiring_soon ? Theme.colors.accentGold
    : cert.verified ? Theme.colors.present
    : Theme.colors.placeholder;
  const icon = cert.is_expired ? 'alert-circle' : cert.expiring_soon ? 'clock-alert-outline' : 'check-decagram-outline';

  return (
    <View style={[styles.certRow, isIssue && styles.certRowAlert]}>
      <MaterialCommunityIcons name={icon as any} size={20} color={iconColor} />
      <View style={styles.certInfo}>
        <Text style={styles.certName}>{cert.name ?? 'Unknown'}</Text>
        {cert.ref && <Text style={styles.certRef}>Ref: {cert.ref}</Text>}
        {cert.expiry_date && (
          <Text style={[styles.certExpiry, { color: iconColor }]}>
            {cert.is_expired ? 'Expired' : cert.expiring_soon ? `Expires in ${cert.days_to_expiry}d` : `Expires ${cert.expiry_date}`}
          </Text>
        )}
      </View>
    </View>
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
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 14 },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2.5,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Theme.colors.surfaceVariant,
  },
  headerInfo: { flex: 1 },
  guardName: { fontSize: 17, fontWeight: 'bold', color: Theme.colors.text },
  gradeBadge: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    backgroundColor: Theme.colors.surfaceVariant,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    marginTop: 4,
    alignSelf: 'flex-start',
  },
  disqRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
  disqText: { fontSize: 11, color: Theme.colors.absent, fontWeight: '600' },
  scoreBlock: { alignItems: 'center', width: 72 },
  scoreNum: { fontSize: 22, fontWeight: 'bold' },
  scoreLabel: { fontSize: 9, color: Theme.colors.placeholder, textTransform: 'uppercase', marginTop: 1 },
  scoreBar: {
    width: 60, height: 5, borderRadius: 3,
    backgroundColor: Theme.colors.surfaceVariant,
    overflow: 'hidden', marginTop: 6,
  },
  scoreFill: { height: 5, borderRadius: 3 },
  attrRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  attrChip: {
    backgroundColor: `${Theme.colors.primary}14`,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  attrText: { fontSize: 10, fontWeight: '600', color: Theme.colors.primary },
  contactRow: { flexDirection: 'row', gap: 10 },
  contactBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1.5,
    borderColor: Theme.colors.primary,
    borderRadius: 10,
    paddingVertical: 8,
  },
  contactLabel: { fontSize: 13, fontWeight: '600', color: Theme.colors.primary },

  sectionTitle: {
    fontSize: 11,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
    marginTop: 4,
  },
  expWarn: { color: Theme.colors.accentGold, textTransform: 'none' },

  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 20,
  },
  todayRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  todayLeft: { flex: 1 },
  todaySite: { fontSize: 15, fontWeight: 'bold', color: Theme.colors.primary },
  todayMeta: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  todayCheckIn: { fontSize: 11, color: Theme.colors.text, marginTop: 4, fontWeight: '600' },
  presenceBadge: {
    borderWidth: 1.5, borderRadius: 10,
    paddingHorizontal: 10, paddingVertical: 4,
  },
  presenceText: { fontSize: 11, fontWeight: '700' },
  notAssigned: { alignItems: 'center', gap: 8, paddingVertical: 8 },
  notAssignedText: { color: Theme.colors.placeholder, fontSize: 13 },

  statsRow: { flexDirection: 'row', gap: 6, marginBottom: 10 },
  statCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    flex: 1,
  },
  statContent: { alignItems: 'center', paddingVertical: 8, paddingHorizontal: 2 },
  statNum: { fontSize: 16, fontWeight: 'bold' },
  statLabel: { fontSize: 8, color: Theme.colors.placeholder, textTransform: 'uppercase', marginTop: 1 },
  rateCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 14,
    marginBottom: 20,
  },
  rateContent: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  rateNum: { fontSize: 24, fontWeight: 'bold' },
  rateLabel: { fontSize: 12, color: Theme.colors.placeholder },

  certRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  certRowAlert: { borderColor: Theme.colors.accentGold, backgroundColor: '#FFFBEB' },
  certInfo: { flex: 1 },
  certName: { fontSize: 13, fontWeight: '600', color: Theme.colors.text },
  certRef: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 1 },
  certExpiry: { fontSize: 11, fontWeight: '600', marginTop: 2 },

  historyRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 6,
  },
  historyLeft: { flex: 1 },
  historyDate: { fontSize: 13, fontWeight: '600', color: Theme.colors.text },
  historyMeta: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  historyRight: { alignItems: 'flex-end' },
  historyPresence: { fontSize: 12, fontWeight: '600' },
  lateText: { fontSize: 10, color: Theme.colors.absent, marginTop: 1 },
});
