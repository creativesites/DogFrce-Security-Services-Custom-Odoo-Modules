import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator, Searchbar } from 'react-native-paper';
import { getAllSites, SiteDaySummary } from '../../src/api/supervisor';
import { Theme } from '../../src/theme';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAppStore } from '../../src/stores/appStore';

function getBatchBadge(state: string) {
  switch (state) {
    case 'draft':     return { label: 'IN PROGRESS', color: Theme.colors.scheduled };
    case 'captured':  return { label: 'CAPTURED', color: Theme.colors.primary };
    case 'confirmed': return { label: 'CONFIRMED', color: Theme.colors.present };
    case 'cancelled': return { label: 'CANCELLED', color: Theme.colors.absent };
    default:          return { label: 'NOT STARTED', color: Theme.colors.placeholder };
  }
}

function SiteCard({ site, onPress }: { site: SiteDaySummary; onPress: () => void }) {
  const badge = getBatchBadge(site.batch_state);
  const rateColor = site.attendance_rate >= 90
    ? Theme.colors.present
    : site.attendance_rate >= 70
    ? Theme.colors.awol
    : Theme.colors.absent;

  return (
    <TouchableOpacity activeOpacity={0.8} onPress={onPress} style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardTitle}>
          <Text style={styles.siteName}>{site.site_name}</Text>
          <Text style={styles.clientName}>{site.client || '—'}</Text>
        </View>
        <View style={[styles.badge, { backgroundColor: `${badge.color}14`, borderColor: badge.color }]}>
          <Text style={[styles.badgeText, { color: badge.color }]}>{badge.label}</Text>
        </View>
      </View>

      {site.has_batch ? (
        <>
          <View style={styles.progressBg}>
            <View style={[styles.progressFg, { width: `${Math.min(site.attendance_rate, 100)}%`, backgroundColor: rateColor }]} />
          </View>

          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={[styles.statNum, { color: Theme.colors.present }]}>{site.present}</Text>
              <Text style={styles.statLabel}>Present</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={[styles.statNum, { color: Theme.colors.absent }]}>{site.absent}</Text>
              <Text style={styles.statLabel}>Absent</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={[styles.statNum, { color: Theme.colors.awol }]}>{site.awol}</Text>
              <Text style={styles.statLabel}>AWOL</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={[styles.statNum, { color: Theme.colors.placeholder }]}>{site.not_marked}</Text>
              <Text style={styles.statLabel}>Unmarked</Text>
            </View>
            <View style={[styles.rateChip, { backgroundColor: `${rateColor}14` }]}>
              <Text style={[styles.rateText, { color: rateColor }]}>{site.attendance_rate}%</Text>
            </View>
          </View>
        </>
      ) : (
        <View style={styles.noShiftRow}>
          <MaterialCommunityIcons name="clipboard-text-off-outline" size={16} color={Theme.colors.placeholder} />
          <Text style={styles.noShiftText}>
            {site.total > 0 ? `${site.total} guards scheduled — shift not started` : 'No shift scheduled today'}
          </Text>
        </View>
      )}

      {site.supervisor && (
        <View style={styles.supervisorRow}>
          <MaterialCommunityIcons name="account-tie" size={13} color={Theme.colors.placeholder} />
          <Text style={styles.supervisorText}>{site.supervisor}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

export default function SupervisorSiteListScreen() {
  const [date, setDate] = useState('');
  const [sites, setSites] = useState<SiteDaySummary[]>([]);
  const [filtered, setFiltered] = useState<SiteDaySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const { refreshTrigger } = useAppStore();
  const router = useRouter();

  const loadSites = async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getAllSites();
      setSites(res.sites);
      setFiltered(res.sites);
      setDate(res.date);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sites.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { loadSites(); }, [refreshTrigger]);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(sites.filter(s =>
      s.site_name.toLowerCase().includes(q) ||
      (s.client || '').toLowerCase().includes(q)
    ));
  }, [search, sites]);

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  const withBatch = filtered.filter(s => s.has_batch).length;
  const pending = filtered.reduce((n, s) => n + s.not_marked, 0);

  return (
    <View style={styles.container}>
      {filtered.length > 0 && (
        <View style={styles.summaryBar}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNum}>{filtered.length}</Text>
            <Text style={styles.summaryLabel}>Sites</Text>
          </View>
          <View style={styles.summaryDivider} />
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNum}>{withBatch}</Text>
            <Text style={styles.summaryLabel}>Active</Text>
          </View>
          <View style={styles.summaryDivider} />
          <View style={styles.summaryItem}>
            <Text style={[styles.summaryNum, pending > 0 && { color: Theme.colors.awol }]}>{pending}</Text>
            <Text style={styles.summaryLabel}>Unmarked</Text>
          </View>
          <View style={styles.summaryDivider} />
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Today</Text>
            <Text style={styles.summaryDate}>{date}</Text>
          </View>
        </View>
      )}

      <Searchbar
        placeholder="Search sites or clients..."
        value={search}
        onChangeText={setSearch}
        style={styles.search}
        inputStyle={{ fontSize: 14, color: Theme.colors.text }}
        placeholderTextColor={Theme.colors.placeholder}
        iconColor={Theme.colors.primary}
      />

      <FlatList
        data={filtered}
        keyExtractor={(item) => item.site_id.toString()}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); loadSites(true); }}
            colors={[Theme.colors.primary]}
            tintColor={Theme.colors.primary}
          />
        }
        renderItem={({ item }) => (
          <SiteCard
            site={item}
            onPress={() => router.push(`/(supervisor)/site/${item.site_id}`)}
          />
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <MaterialCommunityIcons name="office-building-outline" size={48} color={Theme.colors.placeholder} />
            <Text style={styles.emptyText}>{errorMsg || 'No sites found.'}</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  loader: { flex: 1, backgroundColor: Theme.colors.background, justifyContent: 'center', alignItems: 'center' },
  summaryBar: {
    flexDirection: 'row',
    backgroundColor: Theme.colors.surface,
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  summaryItem: { flex: 1, alignItems: 'center' },
  summaryNum: { fontSize: 18, fontWeight: 'bold', color: Theme.colors.text },
  summaryLabel: { fontSize: 10, color: Theme.colors.placeholder, marginTop: 2, fontWeight: '600' },
  summaryDate: { fontSize: 11, color: Theme.colors.text, fontWeight: '600', marginTop: 1 },
  summaryDivider: { width: 1, height: 32, backgroundColor: Theme.colors.border },
  search: {
    margin: 12,
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    elevation: 0,
  },
  list: { paddingHorizontal: 12, paddingBottom: 24 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  cardTitle: { flex: 1, marginRight: 8 },
  siteName: { fontSize: 16, fontWeight: '700', color: Theme.colors.text },
  clientName: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, borderWidth: 1 },
  badgeText: { fontSize: 9, fontWeight: '700' },
  progressBg: { height: 4, backgroundColor: Theme.colors.border, borderRadius: 2, marginBottom: 12, overflow: 'hidden' },
  progressFg: { height: '100%', borderRadius: 2 },
  statsRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 },
  statItem: { alignItems: 'center', flex: 1 },
  statNum: { fontSize: 15, fontWeight: '700' },
  statLabel: { fontSize: 10, color: Theme.colors.placeholder, marginTop: 1, fontWeight: '600' },
  rateChip: { marginLeft: 'auto', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  rateText: { fontSize: 13, fontWeight: '700' },
  noShiftRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  noShiftText: { fontSize: 12, color: Theme.colors.placeholder, flex: 1 },
  supervisorRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: Theme.colors.border },
  supervisorText: { fontSize: 11, color: Theme.colors.placeholder },
  empty: { alignItems: 'center', marginTop: 80, gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14 },
});
