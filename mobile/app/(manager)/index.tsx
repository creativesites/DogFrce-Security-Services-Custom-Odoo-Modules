import React, { useCallback, useEffect, useState } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { getManagerDashboard, ManagerDashboardResponse, getUnassignedSlots, UnassignedSlotsResponse } from '../../src/api/manager';
import { useAppStore } from '../../src/stores/appStore';
import { Theme } from '../../src/theme';
import SiteKpiCard from '../../src/components/SiteKpiCard';
import PeriodNavigator from '../../src/components/PeriodNavigator';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useOfflineQuery } from '../../src/hooks/useOfflineQuery';

function timeAgo(ts: number | null): string {
  if (!ts) return '';
  const diff = Math.floor((Date.now() - ts) / 1000 / 60);
  if (diff < 1) return 'just now';
  if (diff < 60) return `${diff}m ago`;
  return `${Math.floor(diff / 60)}h ago`;
}

export default function ManagerDashboardScreen() {
  const { selectedDate, setSelectedDate, refreshTrigger } = useAppStore();
  const router = useRouter();
  const [gaps, setGaps] = useState<UnassignedSlotsResponse | null>(null);

  const fetcher = useCallback(() => getManagerDashboard(selectedDate), [selectedDate]);
  const { data, isLoading, isRefreshing, isStale, cachedAt, error, refetch } =
    useOfflineQuery<ManagerDashboardResponse>(`manager_dashboard_${selectedDate}`, fetcher);

  useEffect(() => {
    if (refreshTrigger > 0) refetch();
  }, [refreshTrigger]);

  useEffect(() => {
    getUnassignedSlots().then(setGaps).catch(() => {});
  }, [refreshTrigger]);

  if (isLoading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  if (error && !data) {
    return (
      <View style={styles.container}>
        <PeriodNavigator mode="day" value={selectedDate} onChange={setSelectedDate} />
        <View style={styles.emptyState}>
          <MaterialCommunityIcons name="wifi-off" size={52} color={Theme.colors.border} />
          <Text style={styles.emptyTitle}>No data available</Text>
          <Text style={styles.emptyMsg}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={refetch} activeOpacity={0.75}>
            <MaterialCommunityIcons name="refresh" size={16} color="#fff" />
            <Text style={styles.retryLabel}>Retry</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <PeriodNavigator mode="day" value={selectedDate} onChange={setSelectedDate} />

      {isStale && (
        <View style={styles.staleBanner}>
          <MaterialCommunityIcons name="cloud-off-outline" size={13} color={Theme.colors.accentGold} />
          <Text style={styles.staleText}>
            Cached data{cachedAt ? ` · updated ${timeAgo(cachedAt)}` : ''} · Connect to refresh
          </Text>
        </View>
      )}

      <FlatList
        data={data?.sites ?? []}
        keyExtractor={(item) => item.site_id.toString()}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={refetch} colors={[Theme.colors.primary]} />
        }
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <>
            {gaps && gaps.total > 0 && (
              <View style={styles.gapsCard}>
                <View style={styles.gapsHeader}>
                  <MaterialCommunityIcons name="shield-alert-outline" size={16} color="#DC2626" />
                  <Text style={styles.gapsTitle}>Coverage Gaps — Next 7 Days</Text>
                  <View style={styles.gapsBadge}>
                    <Text style={styles.gapsBadgeText}>{gaps.total}</Text>
                  </View>
                </View>
                {gaps.sites.map((site) => (
                  <TouchableOpacity
                    key={site.site_id}
                    style={styles.gapsSiteRow}
                    onPress={() => router.push(`/(manager)/site/${site.site_id}`)}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.gapsSiteName} numberOfLines={1}>{site.site_name}</Text>
                    <View style={styles.gapsSiteRight}>
                      <View style={styles.gapsCountBadge}>
                        <Text style={styles.gapsCountText}>{site.count} unassigned</Text>
                      </View>
                      <MaterialCommunityIcons name="chevron-right" size={14} color="#DC2626" />
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            )}
            {data?.overall ? (
            <View style={styles.summaryBanner}>
              <View style={styles.rateCol}>
                <Text style={styles.rateNum}>{data.overall.attendance_rate}%</Text>
                <Text style={styles.rateLabel}>AVERAGE ATTENDANCE</Text>
              </View>
              <View style={styles.dividerVertical} />
              <View style={styles.gridStats}>
                <View style={styles.gridItem}>
                  <Text style={styles.gridNum}>{data.overall.present}</Text>
                  <Text style={[styles.gridLabel, { color: Theme.colors.present }]}>Present</Text>
                </View>
                <View style={styles.gridItem}>
                  <Text style={styles.gridNum}>{data.overall.late}</Text>
                  <Text style={[styles.gridLabel, { color: Theme.colors.late }]}>Late</Text>
                </View>
                <View style={styles.gridItem}>
                  <Text style={styles.gridNum}>{data.overall.absent}</Text>
                  <Text style={[styles.gridLabel, { color: Theme.colors.absent }]}>Absent</Text>
                </View>
              </View>
            </View>
          ) : null}
          </>
        }
        renderItem={({ item }) => (
          <SiteKpiCard
            siteName={item.site_name}
            client={item.client}
            supervisor={item.supervisor}
            totalSlots={item.total_slots}
            present={item.present}
            absent={item.absent}
            awol={item.awol}
            late={item.late}
            attendanceRate={item.attendance_rate}
            batchState={item.batch_state}
            onPress={() => router.push(`/(manager)/site/${item.site_id}`)}
          />
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <MaterialCommunityIcons name="home-city-outline" size={48} color={Theme.colors.placeholder} />
            <Text style={styles.emptyText}>No sites active today.</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  loader: { flex: 1, backgroundColor: Theme.colors.background, justifyContent: 'center', alignItems: 'center' },
  staleBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: `${Theme.colors.accentGold}18`,
    borderBottomWidth: 1,
    borderBottomColor: `${Theme.colors.accentGold}30`,
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  staleText: { fontSize: 11, color: Theme.colors.accentGold, fontWeight: '600', flex: 1 },
  summaryBanner: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: 20,
    flexDirection: 'row',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
    alignItems: 'center',
    marginBottom: 20,
  },
  rateCol: { alignItems: 'center', flex: 1.2 },
  rateNum: { fontSize: 28, fontWeight: 'bold', color: Theme.colors.text },
  rateLabel: { fontSize: 8, color: Theme.colors.placeholder, fontWeight: 'bold', letterSpacing: 0.5, marginTop: 4 },
  dividerVertical: { width: 1, height: 48, backgroundColor: Theme.colors.border, marginHorizontal: 16 },
  gridStats: { flexDirection: 'row', justifyContent: 'space-between', flex: 2 },
  gridItem: { alignItems: 'center' },
  gridNum: { fontSize: 18, fontWeight: 'bold', color: Theme.colors.text },
  gridLabel: { fontSize: 10, color: Theme.colors.placeholder, fontWeight: '600', marginTop: 2 },
  list: { padding: 16, paddingBottom: 24 },
  empty: { alignItems: 'center', marginTop: 64 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14, marginTop: 12 },
  emptyState: { alignItems: 'center', marginTop: 80, gap: 14, paddingHorizontal: 32 },
  emptyTitle: { fontSize: 18, fontWeight: 'bold', color: Theme.colors.text },
  emptyMsg: { fontSize: 13, color: Theme.colors.placeholder, textAlign: 'center', lineHeight: 20 },
  retryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: Theme.colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 12,
    marginTop: 8,
  },
  retryLabel: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  gapsCard: {
    backgroundColor: '#FFF5F5',
    borderColor: '#FECACA',
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    marginBottom: 16,
    gap: 10,
  },
  gapsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  gapsTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#7F1D1D',
    flex: 1,
  },
  gapsBadge: {
    backgroundColor: '#DC2626',
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  gapsBadgeText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  gapsSiteRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 4,
    paddingVertical: 2,
  },
  gapsSiteRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  gapsSiteName: { fontSize: 13, color: '#7F1D1D', flex: 1 },
  gapsCountBadge: {
    backgroundColor: '#FEE2E2',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  gapsCountText: { fontSize: 11, color: '#DC2626', fontWeight: '700' },
});
