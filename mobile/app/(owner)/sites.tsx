import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator, Card } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { getOwnerSites, OwnerSite, MarginData } from '../../src/api/owner';
import PeriodNavigator from '../../src/components/PeriodNavigator';
import { Theme } from '../../src/theme';

function currentMonth(): string {
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  return `${now.getFullYear()}-${mm}`;
}

function rateColor(rate: number): string {
  if (rate >= 90) return Theme.colors.present;
  if (rate >= 70) return Theme.colors.accentGold;
  return Theme.colors.absent;
}

function stateLabel(state: string): { label: string; color: string } {
  switch (state) {
    case 'confirmed': return { label: 'Submitted', color: Theme.colors.present };
    case 'draft': return { label: 'In Progress', color: Theme.colors.accentGold };
    default: return { label: 'No Batch', color: Theme.colors.placeholder };
  }
}

export default function OwnerSitesScreen() {
  const [sites, setSites] = useState<OwnerSite[]>([]);
  const [period, setPeriod] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(currentMonth);
  const router = useRouter();

  const load = async (month: string, silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getOwnerSites(month);
      setSites(res.sites);
      setPeriod(res.period);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sites.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(selectedMonth); }, [selectedMonth]);

  const onRefresh = () => { setRefreshing(true); load(selectedMonth, true); };

  const renderSite = ({ item }: { item: OwnerSite }) => {
    const state = stateLabel(item.today_state);
    return (
      <TouchableOpacity onPress={() => router.push(`/(owner)/site/${item.site_id}`)} activeOpacity={0.75}>
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.cardHeader}>
            <View style={styles.cardLeft}>
              <Text style={styles.siteName}>{item.name}</Text>
              <Text style={styles.siteClient}>{item.client ?? 'No client'}</Text>
              {item.supervisor && (
                <View style={styles.supervisorRow}>
                  <MaterialCommunityIcons name="account-tie-outline" size={12} color={Theme.colors.placeholder} />
                  <Text style={styles.supervisorName}>{item.supervisor}</Text>
                </View>
              )}
            </View>
            <View style={styles.cardRight}>
              <Text style={[styles.rateNum, { color: rateColor(item.stats.rate) }]}>
                {item.stats.total > 0 ? `${item.stats.rate}%` : '—'}
              </Text>
              <Text style={styles.rateLabel}>{period}</Text>
            </View>
          </View>

          {/* Stats bar */}
          {item.stats.total > 0 && (
            <View style={styles.statsRow}>
              <StatPill value={item.stats.present} label="Present" color={Theme.colors.present} />
              <StatPill value={item.stats.absent} label="Absent" color={Theme.colors.absent} />
              <StatPill value={item.stats.awol} label="AWOL" color={Theme.colors.accentGold} />
              {item.stats.late > 0 && (
                <StatPill value={item.stats.late} label="Late" color={Theme.colors.late} />
              )}
            </View>
          )}

          {/* Margin row */}
          {item.margin && (item.margin.revenue > 0 || item.margin.payroll_cost > 0) && (
            <MarginRow m={item.margin} />
          )}

          {/* Today's batch state */}
          <View style={styles.todayRow}>
            <Text style={styles.todayLabel}>Today:</Text>
            <View style={[styles.stateDot, { backgroundColor: state.color }]} />
            <Text style={[styles.stateText, { color: state.color }]}>{state.label}</Text>
            <MaterialCommunityIcons name="chevron-right" size={16} color={Theme.colors.placeholder} style={{ marginLeft: 'auto' }} />
          </View>
        </Card.Content>
      </Card>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.wrapper}>
      <PeriodNavigator mode="month" value={selectedMonth} onChange={setSelectedMonth} />

      {loading ? (
        <View style={styles.loader}>
          <ActivityIndicator size="large" color={Theme.colors.primary} />
        </View>
      ) : errorMsg ? (
        <View style={styles.errorBox}>
          <MaterialCommunityIcons name="alert-circle-outline" size={32} color={Theme.colors.absent} />
          <Text style={styles.errorText}>{errorMsg}</Text>
        </View>
      ) : (
        <FlatList
          data={sites}
          keyExtractor={(s) => String(s.site_id)}
          renderItem={renderSite}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
          ListHeaderComponent={
            sites.length > 0 ? (
              <Text style={styles.hint}>
                {sites.length} sites · sorted worst → best attendance
              </Text>
            ) : null
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <MaterialCommunityIcons name="office-building-marker-outline" size={40} color={Theme.colors.placeholder} />
              <Text style={styles.emptyText}>No sites found.</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

function StatPill({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <View style={styles.pill}>
      <Text style={[styles.pillNum, { color }]}>{value}</Text>
      <Text style={styles.pillLabel}>{label}</Text>
    </View>
  );
}

function MarginRow({ m }: { m: MarginData }) {
  const marginColor = m.margin >= 0 ? Theme.colors.present : Theme.colors.absent;
  const fmt = (n: number) => `N$${Math.round(n).toLocaleString()}`;
  return (
    <View style={styles.marginRow}>
      <View style={styles.marginItem}>
        <Text style={styles.marginLabel}>Revenue</Text>
        <Text style={styles.marginVal}>{fmt(m.revenue)}</Text>
      </View>
      <View style={styles.marginDivider} />
      <View style={styles.marginItem}>
        <Text style={styles.marginLabel}>Cost</Text>
        <Text style={styles.marginVal}>{fmt(m.payroll_cost)}</Text>
      </View>
      <View style={styles.marginDivider} />
      <View style={styles.marginItem}>
        <Text style={styles.marginLabel}>Margin</Text>
        <Text style={[styles.marginVal, { color: marginColor }]}>
          {fmt(m.margin)}{m.margin_pct !== null ? ` (${m.margin_pct}%)` : ''}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: Theme.colors.background },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorBox: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, padding: 32 },
  errorText: { color: Theme.colors.absent, textAlign: 'center' },
  list: { padding: 16, paddingBottom: 40 },
  hint: { fontSize: 11, color: Theme.colors.placeholder, marginBottom: 12 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 12,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  cardLeft: { flex: 1, marginRight: 8 },
  siteName: { fontSize: 15, fontWeight: 'bold', color: Theme.colors.text },
  siteClient: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  supervisorRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
  supervisorName: { fontSize: 11, color: Theme.colors.placeholder },
  cardRight: { alignItems: 'flex-end' },
  rateNum: { fontSize: 22, fontWeight: 'bold', letterSpacing: -0.5 },
  rateLabel: { fontSize: 10, color: Theme.colors.placeholder, marginTop: 2 },
  statsRow: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  pill: {
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    alignItems: 'center',
    minWidth: 48,
  },
  pillNum: { fontSize: 14, fontWeight: 'bold' },
  pillLabel: { fontSize: 9, color: Theme.colors.placeholder, textTransform: 'uppercase', marginTop: 1 },
  todayRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  todayLabel: { fontSize: 11, color: Theme.colors.placeholder },
  stateDot: { width: 7, height: 7, borderRadius: 4 },
  stateText: { fontSize: 11, fontWeight: '600' },
  empty: { marginTop: 80, alignItems: 'center', gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14 },
  marginRow: {
    flexDirection: 'row',
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    marginBottom: 8,
    alignItems: 'center',
  },
  marginItem: { flex: 1, alignItems: 'center' },
  marginLabel: { fontSize: 9, color: Theme.colors.placeholder, textTransform: 'uppercase', marginBottom: 2 },
  marginVal: { fontSize: 11, fontWeight: '700', color: Theme.colors.text },
  marginDivider: { width: 1, height: 28, backgroundColor: Theme.colors.border },
});
