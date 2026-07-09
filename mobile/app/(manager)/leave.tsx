import React, { useState, useCallback } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useFocusEffect } from 'expo-router';
import { getLeaveRequests, leaveAction, LeaveRequest } from '../../src/api/manager';
import { Theme } from '../../src/theme';

const DAYS_LABEL = (n: number) => `${n} day${n !== 1 ? 's' : ''}`;

function LeaveCard({ req, onApprove, onRefuse, processing }: {
  req: LeaveRequest;
  onApprove: () => void;
  onRefuse: () => void;
  processing: boolean;
}) {
  const gradeBg = req.employee.grade ? `${Theme.colors.accentGold}14` : undefined;

  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={styles.employeeRow}>
          <MaterialCommunityIcons name="shield-account" size={15} color={Theme.colors.primary} />
          <Text style={styles.employeeName}>{req.employee.name}</Text>
          {req.employee.grade && (
            <View style={[styles.gradePill, { backgroundColor: gradeBg, borderColor: Theme.colors.accentGold }]}>
              <Text style={styles.gradeText}>{req.employee.grade}</Text>
            </View>
          )}
        </View>

        <View style={styles.typeRow}>
          <MaterialCommunityIcons name="beach" size={13} color={Theme.colors.placeholder} />
          <Text style={styles.leaveType}>{req.leave_type ?? 'Leave'}</Text>
        </View>

        <View style={styles.dateRow}>
          <MaterialCommunityIcons name="calendar-range" size={13} color={Theme.colors.placeholder} />
          <Text style={styles.dateText}>
            {req.date_from} → {req.date_to}
          </Text>
          <View style={styles.daysBadge}>
            <Text style={styles.daysText}>{DAYS_LABEL(req.requested_days)}</Text>
          </View>
        </View>

        {req.balance_days !== null && (
          <View style={styles.balanceRow}>
            <MaterialCommunityIcons name="wallet-outline" size={12} color={Theme.colors.placeholder} />
            <Text style={styles.balanceText}>
              Balance: {req.balance_days} days remaining
            </Text>
          </View>
        )}
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionBtn, styles.refuseBtn, processing && styles.btnDisabled]}
          onPress={onRefuse}
          disabled={processing}
          activeOpacity={0.75}
        >
          <MaterialCommunityIcons name="close" size={14} color="#DC2626" />
          <Text style={[styles.actionLabel, { color: '#DC2626' }]}>Refuse</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionBtn, styles.approveBtn, processing && styles.btnDisabled]}
          onPress={onApprove}
          disabled={processing}
          activeOpacity={0.75}
        >
          {processing ? (
            <ActivityIndicator size={12} color="#fff" />
          ) : (
            <MaterialCommunityIcons name="check" size={14} color="#fff" />
          )}
          <Text style={[styles.actionLabel, { color: '#fff' }]}>Approve</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export default function LeaveScreen() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError('');
    try {
      const data = await getLeaveRequests();
      setRequests(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load leave requests');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const handleAction = async (req: LeaveRequest, action: 'approve' | 'refuse') => {
    const label = action === 'approve' ? 'Approve' : 'Refuse';
    Alert.alert(
      `${label} Leave`,
      `${label} ${req.employee.name}'s leave request (${DAYS_LABEL(req.requested_days)})?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: label,
          style: action === 'refuse' ? 'destructive' : 'default',
          onPress: async () => {
            setProcessingId(req.id);
            try {
              await leaveAction(req.id, action);
              setRequests((prev) => prev.filter((r) => r.id !== req.id));
            } catch (err: any) {
              Alert.alert('Error', err.message || `Failed to ${action} leave`);
            } finally {
              setProcessingId(null);
            }
          },
        },
      ]
    );
  };

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
        <MaterialCommunityIcons name="calendar-check" size={20} color={Theme.colors.primary} />
        <Text style={styles.pageTitle}>Leave Requests</Text>
        {requests.length > 0 && (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{requests.length}</Text>
          </View>
        )}
      </View>

      {error ? (
        <View style={styles.centered}>
          <MaterialCommunityIcons name="alert-circle-outline" size={40} color={Theme.colors.absent} />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={() => load()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : requests.length === 0 ? (
        <View style={styles.centered}>
          <MaterialCommunityIcons name="check-circle-outline" size={52} color={Theme.colors.present} />
          <Text style={styles.emptyTitle}>All clear</Text>
          <Text style={styles.emptySubtitle}>No pending leave requests</Text>
        </View>
      ) : (
        <FlatList
          data={requests}
          keyExtractor={(r) => String(r.id)}
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
            <LeaveCard
              req={item}
              onApprove={() => handleAction(item, 'approve')}
              onRefuse={() => handleAction(item, 'refuse')}
              processing={processingId === item.id}
            />
          )}
        />
      )}
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
    backgroundColor: Theme.colors.primary,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  countText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  list: { padding: 16, gap: 12 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    overflow: 'hidden',
  },
  cardTop: { padding: 14, gap: 6 },
  employeeRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  employeeName: { fontSize: 15, fontWeight: 'bold', color: Theme.colors.text, flex: 1 },
  gradePill: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 1,
  },
  gradeText: { fontSize: 10, fontWeight: 'bold', color: Theme.colors.accentGold },
  typeRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  leaveType: { fontSize: 13, color: Theme.colors.onSurface },
  dateRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
  dateText: { fontSize: 12, color: Theme.colors.placeholder, flex: 1 },
  daysBadge: {
    backgroundColor: `${Theme.colors.primary}18`,
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  daysText: { fontSize: 11, color: Theme.colors.primary, fontWeight: 'bold' },
  balanceRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 1 },
  balanceText: { fontSize: 11, color: Theme.colors.placeholder },
  actions: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: Theme.colors.border,
  },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 11,
  },
  refuseBtn: {
    borderRightWidth: 0.5,
    borderRightColor: Theme.colors.border,
    backgroundColor: '#FEF2F2',
  },
  approveBtn: {
    backgroundColor: Theme.colors.present,
  },
  actionLabel: { fontSize: 13, fontWeight: '700' },
  btnDisabled: { opacity: 0.5 },
  errorText: { fontSize: 14, color: Theme.colors.absent, textAlign: 'center' },
  retryBtn: {
    marginTop: 4,
    paddingHorizontal: 20,
    paddingVertical: 8,
    backgroundColor: Theme.colors.primary,
    borderRadius: 8,
  },
  retryText: { color: '#fff', fontWeight: '600' },
  emptyTitle: { fontSize: 18, fontWeight: 'bold', color: Theme.colors.text },
  emptySubtitle: { fontSize: 13, color: Theme.colors.placeholder },
});
