import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { Text, Searchbar, Button, FAB, ActivityIndicator } from 'react-native-paper';
import { getTodayPostingSheet, TodayResponse, submitBatch } from '../../src/api/supervisor';
import { useAppStore } from '../../src/stores/appStore';
import { Theme } from '../../src/theme';
import GuardCard from '../../src/components/GuardCard';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function SupervisorTodayScreen() {
  const [data, setData] = useState<TodayResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  const { searchQuery, setSearchQuery, refreshTrigger, triggerRefresh } = useAppStore();
  const router = useRouter();

  const loadData = async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getTodayPostingSheet();
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load today\'s postings.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [refreshTrigger]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData(true);
  };

  const handleSubmit = async () => {
    if (!data || !data.batch_id) return;
    setSubmitting(true);
    try {
      await submitBatch(data.batch_id);
      triggerRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to submit batch.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  // Filter lists based on search
  const filteredSlots = data?.slots
    ? data.slots.filter((s) => s.guard.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : [];

  const filteredFallback = data?.roster_slots
    ? data.roster_slots.filter((s) => s.guard.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : [];

  const isAllMarked = data?.slots && data.slots.every((s) => s.manual_presence !== 'not_marked');

  return (
    <View style={styles.container}>
      <View style={styles.headerBar}>
        <View style={styles.headerInfo}>
          <Text style={styles.siteName}>{data?.site?.name || 'Assigned Sites'}</Text>
          <Text style={styles.dateLabel}>{data?.date || new Date().toDateString()}</Text>
        </View>
        {data?.batch_state && (
          <View style={[styles.stateChip, data.batch_state === 'captured' && styles.capturedChip]}>
            <Text style={styles.stateChipText}>
              {data.batch_state.toUpperCase()}
            </Text>
          </View>
        )}
      </View>

      <Searchbar
        placeholder="Filter guards by name..."
        value={searchQuery}
        onChangeText={setSearchQuery}
        style={styles.search}
        inputStyle={styles.searchInput}
        placeholderTextColor={Theme.colors.placeholder}
        iconColor={Theme.colors.primary}
      />

      {errorMsg ? (
        <View style={styles.errBox}>
          <MaterialCommunityIcons name="alert-circle-outline" size={24} color={Theme.colors.absent} />
          <Text style={styles.errText}>{errorMsg}</Text>
          <Button onPress={() => loadData()} mode="outlined" style={styles.errBtn}>
            Retry
          </Button>
        </View>
      ) : null}

      {!errorMsg && data?.slots ? (
        <FlatList
          data={filteredSlots}
          keyExtractor={(item) => item.record_id.toString()}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <GuardCard
              name={item.guard.name}
              grade={item.guard.grade}
              post={item.post}
              shift={item.shift}
              status={item.manual_presence}
              checkIn={item.check_in}
              checkOut={item.check_out}
              onPress={() => router.push(`/(supervisor)/mark/${item.record_id}`)}
            />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <MaterialCommunityIcons name="shield-off-outline" size={48} color={Theme.colors.placeholder} />
              <Text style={styles.emptyText}>No guards matching search query.</Text>
            </View>
          }
        />
      ) : null}

      {/* Fallback Layout: Show Roster Slots if no attendance batch created */}
      {!errorMsg && data?.roster_slots && !data.slots ? (
        <FlatList
          data={filteredFallback}
          keyExtractor={(item) => item.slot_id.toString()}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <GuardCard
              name={item.guard.name}
              grade={item.guard.grade}
              post={item.post}
              shift={item.shift}
              status="scheduled"
              checkIn={null}
              checkOut={null}
            />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <MaterialCommunityIcons name="clipboard-alert-outline" size={48} color={Theme.colors.placeholder} />
              <Text style={styles.emptyText}>No roster slots scheduled for today.</Text>
            </View>
          }
        />
      ) : null}

      {/* Submit FAB visible only on Draft state */}
      {data?.batch_id && data.batch_state === 'draft' && isAllMarked && (
        <FAB
          icon="check-all"
          label={submitting ? "Submitting..." : "Submit Posting Sheet"}
          style={styles.fab}
          onPress={handleSubmit}
          loading={submitting}
          color="#FFF"
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
  headerBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  headerInfo: {
    flex: 1,
  },
  siteName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
  },
  dateLabel: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    marginTop: 2,
  },
  stateChip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    borderColor: Theme.colors.scheduled,
    borderWidth: 1,
  },
  capturedChip: {
    backgroundColor: 'rgba(99, 102, 241, 0.15)',
    borderColor: Theme.colors.primary,
  },
  stateChipText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#FFF',
  },
  search: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    height: 48,
    justifyContent: 'center',
    marginBottom: 16,
  },
  searchInput: {
    color: Theme.colors.text,
    fontSize: 14,
  },
  list: {
    paddingBottom: 80,
  },
  empty: {
    alignItems: 'center',
    marginTop: 64,
    gap: 12,
  },
  emptyText: {
    color: Theme.colors.placeholder,
    fontSize: 14,
  },
  errBox: {
    alignItems: 'center',
    marginTop: 64,
    gap: 12,
  },
  errText: {
    color: Theme.colors.absent,
    textAlign: 'center',
  },
  errBtn: {
    marginTop: 8,
    borderColor: Theme.colors.absent,
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: Theme.colors.primary,
  },
});
