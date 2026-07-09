import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, StyleSheet, ScrollView, RefreshControl,
  TouchableOpacity, Animated,
} from 'react-native';
import { Text, ActivityIndicator, Card } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import client from '../../../src/api/client';
import { Theme } from '../../../src/theme';

// ─── Types ────────────────────────────────────────────────────────────────────
interface GuardEntry {
  id: number | null;
  name: string;
  grade: string | null;
  presence: 'present' | 'absent' | 'awol' | 'not_marked';
  check_in: string | null;
  late_minutes: number;
  post: string | null;
}

interface SiteEntry {
  site_id: number | null;
  site_name: string;
  batch_id: number;
  batch_state: string;
  supervisor: string | null;
  total: number;
  present: number;
  absent: number;
  awol: number;
  not_marked: number;
  rate: number;
  guards: GuardEntry[];
}

interface LiveSummary {
  total_sites: number;
  sites_submitted: number;
  sites_in_progress: number;
  total_guards: number;
  total_present: number;
  total_absent: number;
  total_awol: number;
  total_not_marked: number;
  overall_rate: number;
}

interface LiveData {
  date: string;
  summary: LiveSummary;
  sites: SiteEntry[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function presenceIcon(p: string): string {
  switch (p) {
    case 'present': return 'check-circle-outline';
    case 'absent': return 'close-circle-outline';
    case 'awol': return 'alert-circle-outline';
    default: return 'circle-outline';
  }
}

function presenceColor(p: string): string {
  switch (p) {
    case 'present': return Theme.colors.present;
    case 'absent': return Theme.colors.absent;
    case 'awol': return Theme.colors.accentGold;
    default: return Theme.colors.placeholder;
  }
}

function severityColor(site: SiteEntry): string {
  if (site.awol > 0) return Theme.colors.absent;
  if (site.absent > 0) return Theme.colors.accentGold;
  if (site.not_marked > 0) return Theme.colors.placeholder;
  return Theme.colors.present;
}

function batchStateLabel(s: string): string {
  switch (s) {
    case 'reviewed': return 'Submitted';
    case 'locked': return 'Locked';
    case 'captured': return 'Captured';
    case 'draft': return 'In Progress';
    default: return 'No Batch';
  }
}

const REFRESH_INTERVAL_MS = 30_000;

// ─── Screen ───────────────────────────────────────────────────────────────────
export default function LiveTimelineScreen() {
  const [liveData, setLiveData] = useState<LiveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchLive = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError('');
    try {
      const res = await client.get('/api/security/mobile/owner/live');
      if (res.data?.success) {
        setLiveData(res.data.data);
        setLastUpdated(new Date());
        // Pulse the indicator on update
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.4, duration: 200, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 200, useNativeDriver: true }),
        ]).start();
      } else {
        setError(res.data?.error || 'Failed to load live data');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchLive();
    intervalRef.current = setInterval(() => fetchLive(true), REFRESH_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchLive]);

  const onRefresh = () => { setRefreshing(true); fetchLive(true); };

  const toggleExpand = (batchId: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(batchId)) next.delete(batchId);
      else next.add(batchId);
      return next;
    });
  };

  if (loading) {
    return <View style={styles.loader}><ActivityIndicator size="large" color={Theme.colors.primary} /></View>;
  }

  if (error) {
    return (
      <View style={styles.errorBox}>
        <MaterialCommunityIcons name="alert-circle-outline" size={40} color={Theme.colors.absent} />
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  if (!liveData) return null;

  const { summary, sites } = liveData;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scroll}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
    >
      {/* ── Header with pulse dot ─────────────────────────────────────────── */}
      <View style={styles.headerRow}>
        <Animated.View style={[styles.liveDot, { transform: [{ scale: pulseAnim }] }]} />
        <Text style={styles.liveLabel}>LIVE</Text>
        <Text style={styles.dateLabel}>{liveData.date}</Text>
        {lastUpdated && (
          <Text style={styles.updatedLabel}>
            Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Text>
        )}
      </View>

      {/* ── Summary bar ───────────────────────────────────────────────────── */}
      <Card style={styles.summaryCard}>
        <Card.Content>
          <View style={styles.summaryRow}>
            <SumBlock label="Sites" value={summary.total_sites} color={Theme.colors.primary} icon="office-building-outline" />
            <SumBlock label="Guards" value={summary.total_guards} color={Theme.colors.text} icon="shield-account-outline" />
            <SumBlock label="Present" value={summary.total_present} color={Theme.colors.present} icon="check-circle-outline" />
            <SumBlock label="Absent" value={summary.total_absent} color={Theme.colors.accentGold} icon="close-circle-outline" />
            <SumBlock label="AWOL" value={summary.total_awol} color={Theme.colors.absent} icon="alert-circle-outline" />
          </View>
          {/* Overall rate bar */}
          <View style={styles.rateBarOuter}>
            <View style={[styles.rateBarFill, { width: `${summary.overall_rate}%` }]} />
          </View>
          <Text style={styles.rateBarLabel}>{summary.overall_rate}% present company-wide</Text>
        </Card.Content>
      </Card>

      {/* ── Submission status chips ────────────────────────────────────────── */}
      <View style={styles.statusChipsRow}>
        <View style={[styles.statusChip, { backgroundColor: `${Theme.colors.present}15` }]}>
          <Text style={[styles.statusChipText, { color: Theme.colors.present }]}>
            {summary.sites_submitted} Submitted
          </Text>
        </View>
        <View style={[styles.statusChip, { backgroundColor: `${Theme.colors.accentGold}15` }]}>
          <Text style={[styles.statusChipText, { color: Theme.colors.accentGold }]}>
            {summary.sites_in_progress} In Progress
          </Text>
        </View>
        {summary.total_not_marked > 0 && (
          <View style={[styles.statusChip, { backgroundColor: `${Theme.colors.placeholder}15` }]}>
            <Text style={[styles.statusChipText, { color: Theme.colors.placeholder }]}>
              {summary.total_not_marked} Unmarked
            </Text>
          </View>
        )}
      </View>

      {/* ── Site cards ────────────────────────────────────────────────────── */}
      {sites.length === 0 ? (
        <View style={styles.empty}>
          <MaterialCommunityIcons name="calendar-blank-outline" size={48} color={Theme.colors.placeholder} />
          <Text style={styles.emptyText}>No attendance batches for today yet.</Text>
        </View>
      ) : (
        sites.map((site) => {
          const isOpen = expanded.has(site.batch_id);
          const accent = severityColor(site);
          return (
            <Card key={site.batch_id} style={[styles.siteCard, { borderLeftColor: accent, borderLeftWidth: 4 }]}>
              <TouchableOpacity onPress={() => toggleExpand(site.batch_id)} activeOpacity={0.8}>
                <Card.Content>
                  <View style={styles.siteCardHeader}>
                    <View style={styles.siteCardLeft}>
                      <Text style={styles.siteName}>{site.site_name}</Text>
                      {site.supervisor && (
                        <Text style={styles.siteSup}>
                          <MaterialCommunityIcons name="account-tie-outline" size={11} color={Theme.colors.placeholder} />
                          {' '}{site.supervisor}
                        </Text>
                      )}
                    </View>
                    <View style={styles.siteCardRight}>
                      <Text style={[styles.siteRate, { color: accent }]}>{site.rate}%</Text>
                      <Text style={[styles.batchState, { color: accent }]}>
                        {batchStateLabel(site.batch_state)}
                      </Text>
                    </View>
                    <MaterialCommunityIcons
                      name={isOpen ? 'chevron-up' : 'chevron-down'}
                      size={20}
                      color={Theme.colors.placeholder}
                      style={{ marginLeft: 8 }}
                    />
                  </View>

                  {/* Mini pill row always visible */}
                  <View style={styles.pillRow}>
                    <MiniPill value={site.present} label="Present" color={Theme.colors.present} />
                    {site.absent > 0 && <MiniPill value={site.absent} label="Absent" color={Theme.colors.accentGold} />}
                    {site.awol > 0 && <MiniPill value={site.awol} label="AWOL" color={Theme.colors.absent} />}
                    {site.not_marked > 0 && <MiniPill value={site.not_marked} label="Unmarked" color={Theme.colors.placeholder} />}
                  </View>

                  {/* Expanded guard list */}
                  {isOpen && (
                    <View style={styles.guardList}>
                      {site.guards.map((g, idx) => (
                        <View key={idx} style={styles.guardRow}>
                          <MaterialCommunityIcons
                            name={presenceIcon(g.presence) as any}
                            size={16}
                            color={presenceColor(g.presence)}
                          />
                          <View style={styles.guardInfo}>
                            <Text style={styles.guardName}>{g.name}</Text>
                            {(g.grade || g.post) && (
                              <Text style={styles.guardMeta}>
                                {[g.grade, g.post].filter(Boolean).join(' · ')}
                              </Text>
                            )}
                          </View>
                          <View style={styles.guardRight}>
                            {g.check_in && (
                              <Text style={styles.checkIn}>{g.check_in}</Text>
                            )}
                            {g.late_minutes > 0 && (
                              <Text style={styles.lateText}>{g.late_minutes}m late</Text>
                            )}
                          </View>
                        </View>
                      ))}
                    </View>
                  )}
                </Card.Content>
              </TouchableOpacity>
            </Card>
          );
        })
      )}
    </ScrollView>
  );
}

function SumBlock({ label, value, color, icon }: { label: string; value: number; color: string; icon: string }) {
  return (
    <View style={styles.sumBlock}>
      <MaterialCommunityIcons name={icon as any} size={18} color={color} />
      <Text style={[styles.sumVal, { color }]}>{value}</Text>
      <Text style={styles.sumLabel}>{label}</Text>
    </View>
  );
}

function MiniPill({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <View style={[styles.miniPill, { borderColor: `${color}40` }]}>
      <Text style={[styles.miniPillNum, { color }]}>{value}</Text>
      <Text style={styles.miniPillLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  scroll: { padding: 16, paddingBottom: 40 },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorBox: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, padding: 32 },
  errorText: { color: Theme.colors.absent, textAlign: 'center' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 14 },
  liveDot: {
    width: 10, height: 10, borderRadius: 5,
    backgroundColor: Theme.colors.present,
  },
  liveLabel: { fontSize: 12, fontWeight: 'bold', color: Theme.colors.present, letterSpacing: 1 },
  dateLabel: { fontSize: 13, color: Theme.colors.text, fontWeight: '600', flex: 1 },
  updatedLabel: { fontSize: 10, color: Theme.colors.placeholder },
  summaryCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 12,
  },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  sumBlock: { alignItems: 'center', gap: 2, flex: 1 },
  sumVal: { fontSize: 18, fontWeight: 'bold' },
  sumLabel: { fontSize: 8, color: Theme.colors.placeholder, textTransform: 'uppercase' },
  rateBarOuter: {
    height: 6, backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 3, overflow: 'hidden', marginBottom: 4,
  },
  rateBarFill: { height: 6, backgroundColor: Theme.colors.present, borderRadius: 3 },
  rateBarLabel: { fontSize: 10, color: Theme.colors.placeholder, textAlign: 'center' },
  statusChipsRow: { flexDirection: 'row', gap: 8, marginBottom: 16, flexWrap: 'wrap' },
  statusChip: { borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5 },
  statusChipText: { fontSize: 11, fontWeight: '600' },
  siteCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 10,
    overflow: 'hidden',
  },
  siteCardHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10 },
  siteCardLeft: { flex: 1 },
  siteName: { fontSize: 15, fontWeight: 'bold', color: Theme.colors.text },
  siteSup: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  siteCardRight: { alignItems: 'flex-end' },
  siteRate: { fontSize: 18, fontWeight: 'bold', letterSpacing: -0.5 },
  batchState: { fontSize: 9, fontWeight: '600', textTransform: 'uppercase', marginTop: 1 },
  pillRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  miniPill: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    borderWidth: 1, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
  },
  miniPillNum: { fontSize: 11, fontWeight: 'bold' },
  miniPillLabel: { fontSize: 9, color: Theme.colors.placeholder, textTransform: 'uppercase' },
  guardList: { marginTop: 12, borderTopWidth: 1, borderTopColor: Theme.colors.border, paddingTop: 10, gap: 8 },
  guardRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  guardInfo: { flex: 1 },
  guardName: { fontSize: 13, color: Theme.colors.text },
  guardMeta: { fontSize: 10, color: Theme.colors.placeholder, marginTop: 1 },
  guardRight: { alignItems: 'flex-end', gap: 2 },
  checkIn: { fontSize: 11, color: Theme.colors.placeholder },
  lateText: { fontSize: 10, color: Theme.colors.accentGold, fontWeight: '600' },
  empty: { alignItems: 'center', marginTop: 60, gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14, textAlign: 'center' },
});
