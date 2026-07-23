import React, { useEffect, useState } from 'react';
import { View, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { Text, ActivityIndicator, Card } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../../src/theme';
import { getGuardHistory, GuardHistoryResponse } from '../../src/api/guard';

export default function GuardHistoryScreen() {
  const [data, setData] = useState<GuardHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const res = await getGuardHistory();
      setData(res);
    } catch (err: any) {
      console.warn('Failed to load guard history:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  const summary = data?.summary || { total_shifts: 0, present: 0, late: 0, absent: 0, attendance_rate: 100 };

  return (
    <View style={styles.container}>
      {/* Attendance Summary Banner */}
      <View style={styles.summaryBar}>
        <View style={styles.statCol}>
          <Text style={styles.statVal}>{summary.attendance_rate}%</Text>
          <Text style={styles.statLbl}>Attendance Rate</Text>
        </View>
        <View style={styles.vDivider} />
        <View style={styles.statCol}>
          <Text style={[styles.statVal, { color: Theme.colors.present }]}>{summary.present}</Text>
          <Text style={styles.statLbl}>Present</Text>
        </View>
        <View style={styles.vDivider} />
        <View style={styles.statCol}>
          <Text style={[styles.statVal, { color: Theme.colors.absent }]}>{summary.absent}</Text>
          <Text style={styles.statLbl}>Absent / AWOL</Text>
        </View>
      </View>

      <FlatList
        data={data?.history || []}
        keyExtractor={(item) => item.record_id.toString()}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); loadData(); }}
            colors={[Theme.colors.primary]}
            tintColor={Theme.colors.primary}
          />
        }
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <Card.Content style={styles.cardContent}>
              <View style={styles.cardHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.siteName}>{item.site}</Text>
                  <Text style={styles.dateText}>{item.date}</Text>
                </View>
                <View style={[styles.statusChip, item.presence === 'present' ? styles.presentChip : styles.absentChip]}>
                  <Text style={[styles.statusText, item.presence === 'present' ? styles.presentText : styles.absentText]}>
                    {item.presence.toUpperCase()}
                  </Text>
                </View>
              </View>

              <View style={styles.metaRow}>
                <Text style={styles.metaText}>Post: {item.post || 'General Duty'}</Text>
                {item.check_in && (
                  <Text style={styles.metaText}>In: {item.check_in.substring(11, 16)}</Text>
                )}
              </View>
            </Card.Content>
          </Card>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <MaterialCommunityIcons name="calendar-blank-outline" size={48} color={Theme.colors.placeholder} />
            <Text style={styles.emptyText}>No attendance records found for the last 30 days.</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Theme.colors.background },
  summaryBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Theme.colors.border,
    paddingVertical: 16,
    paddingHorizontal: 12,
  },
  statCol: { flex: 1, alignItems: 'center' },
  statVal: { fontSize: 20, fontWeight: '800', color: Theme.colors.text },
  statLbl: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  vDivider: { width: 1, height: 28, backgroundColor: Theme.colors.border },
  list: { padding: 16, paddingBottom: 40 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    marginBottom: 12,
    elevation: 0,
  },
  cardContent: { padding: 12 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  siteName: { fontSize: 15, fontWeight: '700', color: Theme.colors.text },
  dateText: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  statusChip: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  presentChip: { backgroundColor: `${Theme.colors.present}15` },
  absentChip: { backgroundColor: `${Theme.colors.absent}15` },
  statusText: { fontSize: 10, fontWeight: '700' },
  presentText: { color: Theme.colors.present },
  absentText: { color: Theme.colors.absent },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderTopColor: Theme.colors.border },
  metaText: { fontSize: 12, color: Theme.colors.placeholder },
  empty: { alignItems: 'center', marginTop: 64, gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14 },
});
