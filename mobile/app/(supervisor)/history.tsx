import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator, Button } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { getHistory, HistoryBatch, HistoryResponse } from '../../src/api/supervisor';
import { generateHistoryReportPDF } from '../../src/utils/pdfExport';
import { Theme } from '../../src/theme';

const PAGE_SIZE = 20;

export default function SupervisorHistoryScreen() {
  const [batches, setBatches] = useState<HistoryBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  const loadPage = useCallback(async (reset = false) => {
    const currentOffset = reset ? 0 : offset;
    if (!reset && loadingMore) return;
    reset ? setLoading(true) : setLoadingMore(true);
    if (reset) setBatches([]);
    setErrorMsg('');
    try {
      const res: HistoryResponse = await getHistory(PAGE_SIZE, currentOffset);
      const newBatches = res.batches || [];
      setBatches(prev => reset ? newBatches : [...prev, ...newBatches]);
      setTotal(res.pagination?.total ?? 0);
      setOffset(currentOffset + newBatches.length);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load history.');
    } finally {
      setLoading(false);
      setLoadingMore(false);
      setRefreshing(false);
    }
  }, [offset, loadingMore]);

  useEffect(() => { loadPage(true); }, []);

  const onRefresh = () => { setRefreshing(true); setOffset(0); loadPage(true); };
  const onEndReached = () => { if (batches.length < total) loadPage(false); };

  const handleExportPDF = async () => {
    if (!batches.length) return;
    setExporting(true);
    try {
      await generateHistoryReportPDF(batches);
    } catch (err: any) {
      setErrorMsg('Export failed: ' + (err.message || 'Unknown error'));
    } finally {
      setExporting(false);
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'confirmed': return Theme.colors.present;
      case 'captured':  return Theme.colors.primary;
      default:          return Theme.colors.placeholder;
    }
  };

  const renderItem = ({ item }: { item: HistoryBatch }) => {
    const rate = item.summary.attendance_rate;
    const rateColor = rate >= 90 ? Theme.colors.present : rate >= 75 ? Theme.colors.awol : Theme.colors.absent;

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={styles.cardLeft}>
            <Text style={styles.siteName}>{item.site?.name ?? 'Unknown Site'}</Text>
            <Text style={styles.dateText}>{item.date}</Text>
          </View>
          <View style={[styles.stateBadge, { borderColor: getStateColor(item.state) }]}>
            <Text style={[styles.stateText, { color: getStateColor(item.state) }]}>
              {item.state.toUpperCase()}
            </Text>
          </View>
        </View>

        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <MaterialCommunityIcons name="account-check" size={15} color={Theme.colors.present} />
            <Text style={styles.statNum}>{item.summary.present}</Text>
            <Text style={styles.statLabel}>Present</Text>
          </View>
          <View style={styles.statItem}>
            <MaterialCommunityIcons name="account-clock" size={15} color={Theme.colors.awol} />
            <Text style={styles.statNum}>{item.summary.late}</Text>
            <Text style={styles.statLabel}>Late</Text>
          </View>
          <View style={styles.statItem}>
            <MaterialCommunityIcons name="account-off" size={15} color={Theme.colors.absent} />
            <Text style={styles.statNum}>{item.summary.absent + item.summary.awol}</Text>
            <Text style={styles.statLabel}>Absent</Text>
          </View>
          <View style={[styles.rateChip, { backgroundColor: `${rateColor}14` }]}>
            <Text style={[styles.rateText, { color: rateColor }]}>{rate}%</Text>
          </View>
        </View>
      </View>
    );
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
      <View style={styles.headerBar}>
        <Text style={styles.headerTitle}>Batch Log ({total})</Text>
        <Button
          mode="contained-tonal"
          icon="file-pdf-box"
          onPress={handleExportPDF}
          loading={exporting}
          disabled={exporting || !batches.length}
          compact
        >
          Export PDF
        </Button>
      </View>
      <FlatList
        data={batches}
        keyExtractor={(item) => item.batch_id.toString()}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={[Theme.colors.primary]}
            tintColor={Theme.colors.primary}
          />
        }
        onEndReached={onEndReached}
        onEndReachedThreshold={0.3}
        ListFooterComponent={
          loadingMore ? <ActivityIndicator style={styles.footer} color={Theme.colors.primary} /> : null
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <MaterialCommunityIcons name="history" size={48} color={Theme.colors.placeholder} />
              <Text style={styles.emptyText}>{errorMsg || 'No posting history found.'}</Text>
            </View>
          ) : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  headerTitle: { fontSize: 16, fontWeight: '700', color: Theme.colors.text },
  loader: { flex: 1, backgroundColor: Theme.colors.background, justifyContent: 'center', alignItems: 'center' },
  list: { padding: 16, paddingBottom: 40 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  cardLeft: { flex: 1 },
  siteName: { fontSize: 15, fontWeight: '700', color: Theme.colors.text },
  dateText: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  stateBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, borderWidth: 1 },
  stateText: { fontSize: 10, fontWeight: '700' },
  statsRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  statItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  statNum: { fontSize: 13, fontWeight: '600', color: Theme.colors.text },
  statLabel: { fontSize: 11, color: Theme.colors.placeholder },
  rateChip: { marginLeft: 'auto', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  rateText: { fontSize: 12, fontWeight: '700' },
  empty: { alignItems: 'center', marginTop: 80, gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14, textAlign: 'center' },
  footer: { paddingVertical: 16 },
});
