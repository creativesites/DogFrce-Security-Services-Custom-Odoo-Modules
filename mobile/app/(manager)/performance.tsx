import React, { useState, useCallback } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { Text, ActivityIndicator, Portal, Modal, TextInput } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useFocusEffect } from 'expo-router';
import {
  getGuardPerformance,
  initiateGuardReview,
  FlaggedGuard,
  PerformanceFlag,
} from '../../src/api/manager';
import { Theme } from '../../src/theme';

type FilterType = 'all' | 'late' | 'awol' | 'ot';

const FLAG_COLOR: Record<string, string> = {
  late: Theme.colors.accentGold,
  awol: Theme.colors.absent,
  ot: Theme.colors.primary,
};

const FLAG_ICON: Record<string, string> = {
  late: 'clock-alert-outline',
  awol: 'account-alert-outline',
  ot: 'timer-sand',
};

function FlagChip({ flag }: { flag: PerformanceFlag }) {
  const color = FLAG_COLOR[flag.type] || Theme.colors.placeholder;
  const icon = FLAG_ICON[flag.type] || 'alert-circle-outline';
  return (
    <View style={[styles.flagChip, { backgroundColor: `${color}14`, borderColor: `${color}40` }]}>
      <MaterialCommunityIcons name={icon as any} size={12} color={color} />
      <Text style={[styles.flagChipText, { color }]}>{flag.label}</Text>
    </View>
  );
}

function GuardFlagCard({
  guard,
  onReview,
  onDismiss,
}: {
  guard: FlaggedGuard;
  onReview: () => void;
  onDismiss: () => void;
}) {
  const hasAwol = guard.awol_count >= 2;
  const accentColor = hasAwol ? Theme.colors.absent : Theme.colors.accentGold;

  return (
    <View style={[styles.card, { borderLeftColor: accentColor }]}>
      <View style={styles.cardTop}>
        <View style={styles.empRow}>
          <MaterialCommunityIcons name="shield-account" size={16} color={accentColor} />
          <Text style={styles.empName}>{guard.name}</Text>
          {guard.grade && (
            <View style={[styles.gradePill, { borderColor: Theme.colors.accentGold }]}>
              <Text style={styles.gradeText}>{guard.grade}</Text>
            </View>
          )}
        </View>
        <View style={styles.flagsRow}>
          {guard.flags.map((f, i) => (
            <FlagChip key={i} flag={f} />
          ))}
        </View>
      </View>
      <View style={styles.cardActions}>
        <TouchableOpacity style={styles.dismissBtn} onPress={onDismiss} activeOpacity={0.75}>
          <Text style={styles.dismissText}>Dismiss</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.reviewBtn} onPress={onReview} activeOpacity={0.75}>
          <MaterialCommunityIcons name="clipboard-check-outline" size={14} color="#fff" />
          <Text style={styles.reviewText}>Initiate Review</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export default function PerformanceScreen() {
  const [guards, setGuards] = useState<FlaggedGuard[]>([]);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');

  const [reviewTarget, setReviewTarget] = useState<FlaggedGuard | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewing, setReviewing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError('');
    try {
      const data = await getGuardPerformance();
      setGuards(data.guards);
      setDismissed(new Set()); // reset dismissals on refresh
    } catch (err: any) {
      setError(err.message || 'Failed to load performance data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const openReview = (guard: FlaggedGuard) => {
    setReviewTarget(guard);
    setReviewNote(
      `Performance review initiated for ${guard.name}. ` +
      (guard.awol_count >= 2 ? `${guard.awol_count} AWOLs recorded in the last 30 days. ` : '') +
      (guard.late_count >= 3 ? `${guard.late_count} late arrivals in the last 30 days. ` : '') +
      (guard.ot_hours > 20 ? `${guard.ot_hours}h OT this month. ` : '')
    );
  };

  const submitReview = async () => {
    if (!reviewTarget) return;
    setReviewing(true);
    try {
      await initiateGuardReview(reviewTarget.id, reviewNote);
      setDismissed((prev) => new Set(prev).add(reviewTarget.id));
      setReviewTarget(null);
      Alert.alert('Review Initiated', `A note has been logged on ${reviewTarget.name}'s record in Odoo.`);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to initiate review');
    } finally {
      setReviewing(false);
    }
  };

  const dismiss = (guardId: number) => {
    setDismissed((prev) => new Set(prev).add(guardId));
  };

  const visible = guards.filter((g) => {
    if (dismissed.has(g.id)) return false;
    if (filter === 'all') return true;
    return g.flags.some((f) => f.type === filter);
  });

  const FILTERS: { key: FilterType; label: string; icon: string }[] = [
    { key: 'all', label: 'All', icon: 'filter-variant' },
    { key: 'awol', label: 'AWOL', icon: 'account-alert-outline' },
    { key: 'late', label: 'Late', icon: 'clock-alert-outline' },
    { key: 'ot', label: 'OT High', icon: 'timer-sand' },
  ];

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.pageHeader}>
        <MaterialCommunityIcons name="shield-alert" size={20} color={Theme.colors.absent} />
        <Text style={styles.pageTitle}>Performance Flags</Text>
        {visible.length > 0 && (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{visible.length}</Text>
          </View>
        )}
      </View>

      {/* Filter chips */}
      <View style={styles.filterRow}>
        {FILTERS.map((f) => {
          const active = filter === f.key;
          return (
            <TouchableOpacity
              key={f.key}
              style={[styles.filterChip, active && styles.filterChipActive]}
              onPress={() => setFilter(f.key)}
              activeOpacity={0.75}
            >
              <MaterialCommunityIcons
                name={f.icon as any}
                size={13}
                color={active ? '#fff' : Theme.colors.placeholder}
              />
              <Text style={[styles.filterLabel, active && styles.filterLabelActive]}>{f.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {error ? (
        <View style={styles.centered}>
          <MaterialCommunityIcons name="alert-circle-outline" size={40} color={Theme.colors.absent} />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={() => load()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : visible.length === 0 ? (
        <View style={styles.centered}>
          <MaterialCommunityIcons name="check-decagram-outline" size={52} color={Theme.colors.present} />
          <Text style={styles.emptyTitle}>No flags</Text>
          <Text style={styles.emptySubtitle}>All guards within acceptable thresholds</Text>
        </View>
      ) : (
        <FlatList
          data={visible}
          keyExtractor={(g) => String(g.id)}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => load(true)}
              colors={[Theme.colors.primary]}
              tintColor={Theme.colors.primary}
            />
          }
          renderItem={({ item }) => (
            <GuardFlagCard
              guard={item}
              onReview={() => openReview(item)}
              onDismiss={() => dismiss(item.id)}
            />
          )}
        />
      )}

      {/* Review note modal */}
      <Portal>
        <Modal
          visible={!!reviewTarget}
          onDismiss={() => setReviewTarget(null)}
          contentContainerStyle={styles.modal}
        >
          {reviewTarget && (
            <>
              <Text style={styles.modalTitle}>Initiate Review</Text>
              <Text style={styles.modalSub}>{reviewTarget.name}</Text>
              <TextInput
                label="Review note (saved to Odoo)"
                value={reviewNote}
                onChangeText={setReviewNote}
                mode="outlined"
                multiline
                numberOfLines={4}
                style={styles.noteInput}
                outlineColor={Theme.colors.border}
                activeOutlineColor={Theme.colors.primary}
              />
              <View style={styles.modalBtns}>
                <TouchableOpacity
                  style={[styles.modalBtn, styles.cancelBtn]}
                  onPress={() => setReviewTarget(null)}
                >
                  <Text style={styles.cancelText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.modalBtn, styles.confirmBtn, reviewing && styles.btnDisabled]}
                  onPress={submitReview}
                  disabled={reviewing}
                >
                  {reviewing ? (
                    <ActivityIndicator size={14} color="#fff" />
                  ) : (
                    <MaterialCommunityIcons name="check" size={14} color="#fff" />
                  )}
                  <Text style={styles.confirmText}>Log Review</Text>
                </TouchableOpacity>
              </View>
            </>
          )}
        </Modal>
      </Portal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, padding: 32 },
  pageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  pageTitle: { fontSize: 20, fontWeight: 'bold', color: Theme.colors.text, flex: 1 },
  countBadge: {
    backgroundColor: Theme.colors.absent,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  countText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  filterRow: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  filterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    backgroundColor: Theme.colors.surface,
  },
  filterChipActive: {
    backgroundColor: Theme.colors.primary,
    borderColor: Theme.colors.primary,
  },
  filterLabel: { fontSize: 12, color: Theme.colors.placeholder, fontWeight: '600' },
  filterLabelActive: { color: '#fff' },
  list: { padding: 16, gap: 12 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    borderLeftWidth: 4,
    overflow: 'hidden',
  },
  cardTop: { padding: 14, gap: 8 },
  empRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  empName: { fontSize: 15, fontWeight: 'bold', color: Theme.colors.text, flex: 1 },
  gradePill: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 1,
    backgroundColor: `${Theme.colors.accentGold}14`,
  },
  gradeText: { fontSize: 10, fontWeight: 'bold', color: Theme.colors.accentGold },
  flagsRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  flagChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
  },
  flagChipText: { fontSize: 11, fontWeight: '600' },
  cardActions: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: Theme.colors.border,
  },
  dismissBtn: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRightWidth: 0.5,
    borderRightColor: Theme.colors.border,
  },
  dismissText: { fontSize: 13, color: Theme.colors.placeholder, fontWeight: '600' },
  reviewBtn: {
    flex: 2,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    backgroundColor: Theme.colors.primary,
  },
  reviewText: { fontSize: 13, color: '#fff', fontWeight: '700' },
  errorText: { fontSize: 14, color: Theme.colors.absent, textAlign: 'center' },
  retryBtn: {
    paddingHorizontal: 20,
    paddingVertical: 8,
    backgroundColor: Theme.colors.primary,
    borderRadius: 8,
  },
  retryText: { color: '#fff', fontWeight: '600' },
  emptyTitle: { fontSize: 18, fontWeight: 'bold', color: Theme.colors.text },
  emptySubtitle: { fontSize: 13, color: Theme.colors.placeholder, textAlign: 'center' },
  modal: {
    backgroundColor: Theme.colors.surface,
    borderRadius: 24,
    padding: 24,
    margin: 20,
    borderWidth: 1,
    borderColor: Theme.colors.border,
  },
  modalTitle: { fontSize: 18, fontWeight: 'bold', color: Theme.colors.text, marginBottom: 4 },
  modalSub: { fontSize: 13, color: Theme.colors.placeholder, marginBottom: 16 },
  noteInput: { backgroundColor: Theme.colors.background, marginBottom: 20 },
  modalBtns: { flexDirection: 'row', gap: 12 },
  modalBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: 10,
  },
  cancelBtn: { backgroundColor: Theme.colors.surfaceVariant },
  cancelText: { fontSize: 14, fontWeight: '600', color: Theme.colors.onSurface },
  confirmBtn: { backgroundColor: Theme.colors.primary },
  confirmText: { fontSize: 14, fontWeight: '700', color: '#fff' },
  btnDisabled: { opacity: 0.5 },
});
