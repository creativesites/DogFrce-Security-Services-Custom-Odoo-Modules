import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { getManagerDashboard, ManagerDashboardResponse } from '../../src/api/manager';
import { useAppStore } from '../../src/stores/appStore';
import { Theme } from '../../src/theme';
import SiteKpiCard from '../../src/components/SiteKpiCard';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function ManagerDashboardScreen() {
  const [data, setData] = useState<ManagerDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const { selectedDate, refreshTrigger, triggerRefresh } = useAppStore();
  const router = useRouter();

  const loadDashboard = async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getManagerDashboard(selectedDate);
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch manager dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, [selectedDate, refreshTrigger]);

  const onRefresh = () => {
    setRefreshing(true);
    loadDashboard(true);
  };

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Top Banner KPI Summary */}
      {data?.overall && (
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
      )}

      {errorMsg ? (
        <View style={styles.errorContainer}>
          <MaterialCommunityIcons name="alert-circle-outline" size={32} color={Theme.colors.absent} />
          <Text style={styles.errorText}>{errorMsg}</Text>
        </View>
      ) : null}

      {!errorMsg && data?.sites && (
        <FlatList
          data={data.sites}
          keyExtractor={(item) => item.site_id.toString()}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              colors={[Theme.colors.primary]}
            />
          }
          contentContainerStyle={styles.list}
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
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    padding: 16,
  },
  loader: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    justifyContent: 'center',
    alignItems: 'center',
  },
  summaryBanner: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  rateCol: {
    alignItems: 'center',
    flex: 1.2,
  },
  rateNum: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFF',
  },
  rateLabel: {
    fontSize: 8,
    color: Theme.colors.placeholder,
    fontWeight: 'bold',
    letterSpacing: 0.5,
    marginTop: 4,
  },
  dividerVertical: {
    width: 1,
    height: 48,
    backgroundColor: Theme.colors.border,
    marginHorizontal: 16,
  },
  gridStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    flex: 2,
  },
  gridItem: {
    alignItems: 'center',
  },
  gridNum: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFF',
  },
  gridLabel: {
    fontSize: 10,
    color: Theme.colors.placeholder,
    fontWeight: '600',
    marginTop: 2,
  },
  list: {
    paddingBottom: 24,
  },
  empty: {
    alignItems: 'center',
    marginTop: 64,
  },
  emptyText: {
    color: Theme.colors.placeholder,
    fontSize: 14,
    marginTop: 12,
  },
  errorContainer: {
    alignItems: 'center',
    marginTop: 64,
    gap: 12,
  },
  errorText: {
    color: Theme.colors.absent,
    textAlign: 'center',
  },
});
