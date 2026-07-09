import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Animated,
} from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { getOwnerKpis, OwnerKpisResponse } from '../../src/api/owner';
import { Theme } from '../../src/theme';
import KpiMetric from '../../src/components/KpiMetric';
import AnimatedRingKpi from '../../src/components/AnimatedRingKpi';
import PeriodNavigator from '../../src/components/PeriodNavigator';
import MiniBarChart from '../../src/components/MiniBarChart';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useOfflineQuery } from '../../src/hooks/useOfflineQuery';

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function useCountUp(target: number, duration = 900): number {
  const [display, setDisplay] = useState(0);
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    anim.setValue(0);
    Animated.timing(anim, { toValue: target, duration, useNativeDriver: false }).start();
    const id = anim.addListener(({ value }) => setDisplay(value));
    return () => anim.removeListener(id);
  }, [target]);
  return display;
}

function timeAgo(ts: number | null): string {
  if (!ts) return '';
  const diff = Math.floor((Date.now() - ts) / 1000 / 60);
  if (diff < 1) return 'just now';
  if (diff < 60) return `${diff}m ago`;
  return `${Math.floor(diff / 60)}h ago`;
}

export default function OwnerDashboardScreen() {
  const [selectedMonth, setSelectedMonth] = useState(currentMonth);
  const router = useRouter();
  const cardsFadeAnim = useRef(new Animated.Value(0)).current;

  const fetcher = useCallback(() => getOwnerKpis(selectedMonth), [selectedMonth]);
  const { data, isLoading, isRefreshing, isStale, cachedAt, error, refetch } =
    useOfflineQuery<OwnerKpisResponse>(`owner_kpis_${selectedMonth}`, fetcher);

  useEffect(() => {
    if (data) {
      cardsFadeAnim.setValue(0);
      Animated.timing(cardsFadeAnim, { toValue: 1, duration: 400, delay: 80, useNativeDriver: true }).start();
    }
  }, [data]);

  if (isLoading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
        <Text style={styles.loaderText}>Loading dashboard…</Text>
      </View>
    );
  }

  return (
    <View style={styles.wrapper}>
      <PeriodNavigator mode="month" value={selectedMonth} onChange={setSelectedMonth} />

      {isStale && (
        <View style={styles.staleBanner}>
          <MaterialCommunityIcons name="cloud-off-outline" size={13} color={Theme.colors.accentGold} />
          <Text style={styles.staleText}>
            Cached data{cachedAt ? ` · updated ${timeAgo(cachedAt)}` : ''} · Connect to refresh
          </Text>
        </View>
      )}

      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={refetch} colors={[Theme.colors.primary]} />
        }
      >
        {error && !data ? (
          <OfflineEmptyState message={error} onRetry={refetch} />
        ) : data ? (
          <AnimatedDashboard
            data={data}
            selectedMonth={selectedMonth}
            setSelectedMonth={setSelectedMonth}
            fadeAnim={cardsFadeAnim}
            router={router}
          />
        ) : null}
      </ScrollView>
    </View>
  );
}

function OfflineEmptyState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <View style={styles.emptyState}>
      <MaterialCommunityIcons name="wifi-off" size={52} color={Theme.colors.border} />
      <Text style={styles.emptyTitle}>No data available</Text>
      <Text style={styles.emptyMsg}>{message}</Text>
      <TouchableOpacity style={styles.retryBtn} onPress={onRetry} activeOpacity={0.75}>
        <MaterialCommunityIcons name="refresh" size={16} color="#fff" />
        <Text style={styles.retryLabel}>Retry</Text>
      </TouchableOpacity>
    </View>
  );
}

function AnimatedFinVal({ value, color }: { value: number; color?: string }) {
  const displayed = useCountUp(value);
  return (
    <Text style={[styles.finVal, color ? { color } : {}]}>
      N${Math.round(displayed).toLocaleString()}
    </Text>
  );
}

interface DashboardProps {
  data: OwnerKpisResponse;
  selectedMonth: string;
  setSelectedMonth: (m: string) => void;
  fadeAnim: Animated.Value;
  router: ReturnType<typeof useRouter>;
}

function AnimatedDashboard({ data, selectedMonth, setSelectedMonth, fadeAnim, router }: DashboardProps) {
  return (
    <Animated.View style={[styles.kpiGrid, { opacity: fadeAnim }]}>
      <View style={styles.row}>
        <AnimatedRingKpi
          title="Attendance Rate"
          percent={data.attendance.rate_percent}
          icon="account-check-outline"
          color={Theme.colors.present}
          subtitle="Target: 95%"
        />
        <KpiMetric
          title="Active Guards"
          value={data.total_guards}
          icon="shield-account-outline"
          color={Theme.colors.primary}
          subtitle="On payroll active list"
        />
      </View>

      <View style={styles.row}>
        <KpiMetric
          title="Open Incidents"
          value={data.open_incidents}
          icon="alert-octagon-outline"
          color={Theme.colors.absent}
          subtitle="Immediate action required"
        />
        <KpiMetric
          title="Active Sites"
          value={data.sites_active}
          icon="office-building-marker-outline"
          color={Theme.colors.accentCyan}
          subtitle="Revenue generating posts"
        />
      </View>

      <View style={styles.financialCard}>
        <Text style={styles.financialHeader}>FINANCIAL SUMMARY</Text>
        <View style={styles.financialRow}>
          <View style={styles.financialBlock}>
            <Text style={styles.finLabel}>Payroll Cost YTD</Text>
            <AnimatedFinVal value={data.payroll_cost_ytd} />
          </View>
          <View style={styles.dividerVertical} />
          <View style={styles.financialBlock}>
            <Text style={styles.finLabel}>Outstanding Invoices</Text>
            <AnimatedFinVal value={data.outstanding_invoices} color={Theme.colors.accentGold} />
          </View>
        </View>
      </View>

      {data.monthly_payroll_trend?.length > 0 && (
        <View style={styles.chartCard}>
          <View style={styles.chartHeaderRow}>
            <Text style={styles.financialHeader}>PAYROLL TREND (6 MONTHS)</Text>
            <Text style={styles.chartHint}>Tap bar to filter</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chartScroll}>
            {(() => {
              const trend = data.monthly_payroll_trend;
              const selectedIdx = trend.findIndex((m) => m.month_key === selectedMonth);
              return (
                <MiniBarChart
                  data={trend.map((m) => ({ label: m.month.split(' ')[0], value: m.cost }))}
                  height={72}
                  barColor={Theme.colors.primary}
                  selectedIndex={selectedIdx >= 0 ? selectedIdx : trend.length - 1}
                  onBarPress={(i) => setSelectedMonth(trend[i].month_key)}
                />
              );
            })()}
          </ScrollView>
        </View>
      )}

      <Text style={styles.sectionTitle}>Top Sites By Attendance</Text>
      {data.top_sites_by_attendance?.map((site, idx) => (
        <SiteCardAnimated
          key={site.site_id}
          site={site}
          index={idx}
          onPress={() => router.push(`/(owner)/site/${site.site_id}`)}
        />
      ))}
    </Animated.View>
  );
}

function SiteCardAnimated({
  site,
  index,
  onPress,
}: {
  site: OwnerKpisResponse['top_sites_by_attendance'][0];
  index: number;
  onPress: () => void;
}) {
  const slideAnim = useRef(new Animated.Value(20)).current;
  const opacityAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(slideAnim, { toValue: 0, duration: 300, delay: index * 60, useNativeDriver: true }),
      Animated.timing(opacityAnim, { toValue: 1, duration: 300, delay: index * 60, useNativeDriver: true }),
    ]).start();
  }, []);

  return (
    <Animated.View style={{ opacity: opacityAnim, transform: [{ translateY: slideAnim }] }}>
      <TouchableOpacity onPress={onPress} activeOpacity={0.75}>
        <View style={styles.topSiteCard}>
          <View style={styles.topSiteContent}>
            <View style={styles.topSiteInfo}>
              <Text style={styles.topSiteName}>{site.site_name}</Text>
              <Text style={styles.topSiteClient}>{site.client}</Text>
            </View>
            <View style={styles.topSiteRateBox}>
              <Text style={styles.topSiteRate}>{site.attendance_rate}%</Text>
              <Text style={styles.topSiteLabel}>ATTENDANCE</Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={16} color={Theme.colors.placeholder} style={{ marginLeft: 8 }} />
          </View>
        </View>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: Theme.colors.background },
  container: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  loader: { flex: 1, backgroundColor: Theme.colors.background, justifyContent: 'center', alignItems: 'center', gap: 12 },
  loaderText: { color: Theme.colors.placeholder, fontSize: 13 },
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
  kpiGrid: { gap: 16 },
  row: { flexDirection: 'row', gap: 16 },
  financialCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 20,
    padding: 20,
    marginTop: 8,
  },
  financialHeader: {
    fontSize: 10,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    letterSpacing: 1,
    marginBottom: 16,
  },
  financialRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  financialBlock: { flex: 1 },
  finLabel: { fontSize: 12, color: Theme.colors.placeholder, marginBottom: 4 },
  finVal: { fontSize: 20, fontWeight: 'bold', color: Theme.colors.text, letterSpacing: -0.5 },
  dividerVertical: { width: 1, height: 40, backgroundColor: Theme.colors.border, marginHorizontal: 16 },
  chartCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 20,
    padding: 20,
    marginTop: 8,
  },
  chartHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  chartHint: { fontSize: 10, color: Theme.colors.placeholder, fontStyle: 'italic' },
  chartScroll: { marginTop: 8 },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 16,
    marginBottom: 8,
  },
  topSiteCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 10,
    padding: 16,
  },
  topSiteContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  topSiteInfo: { flex: 1 },
  topSiteName: { fontSize: 15, fontWeight: 'bold', color: Theme.colors.text },
  topSiteClient: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  topSiteRateBox: { alignItems: 'flex-end' },
  topSiteRate: { fontSize: 16, fontWeight: 'bold', color: Theme.colors.present },
  topSiteLabel: { fontSize: 8, color: Theme.colors.placeholder, fontWeight: 'bold', marginTop: 2 },
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
});
