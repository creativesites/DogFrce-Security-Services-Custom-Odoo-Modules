import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { Text, Card, Button, ActivityIndicator, Portal, Modal, TextInput } from 'react-native-paper';
import { Theme } from '../../src/theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { getOvertimeList, approveOvertime, OvertimeRecord, getOtSummary, OtSummaryResponse } from '../../src/api/manager';

export default function GlobalOvertimeScreen() {
  const [records, setRecords] = useState<OvertimeRecord[]>([]);
  const [otSummary, setOtSummary] = useState<OtSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [selected, setSelected] = useState<OvertimeRecord | null>(null);
  const [note, setNote] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const load = async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const [data, summary] = await Promise.all([getOvertimeList(), getOtSummary().catch(() => null)]);
      setRecords(data);
      setOtSummary(summary);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load overtime records.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAction = async (approved: boolean) => {
    if (!selected) return;
    setActionLoading(true);
    try {
      await approveOvertime(selected.record_id, approved, note);
      setRecords(prev => prev.filter(r => r.record_id !== selected.record_id));
      setSelected(null);
      setNote('');
    } catch (err: any) {
      alert(err.message || 'Action failed.');
    } finally {
      setActionLoading(false);
    }
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
      <FlatList
        data={records}
        keyExtractor={(item) => item.record_id.toString()}
        contentContainerStyle={styles.list}
        ListHeaderComponent={otSummary ? (
          <View style={styles.budgetCard}>
            <View style={styles.budgetHeader}>
              <MaterialCommunityIcons name="chart-timeline-variant" size={16} color={Theme.colors.primary} />
              <Text style={styles.budgetTitle}>OT Budget — {otSummary.month}</Text>
              <Text style={styles.budgetDays}>Day {otSummary.days_elapsed}/{otSummary.days_in_month}</Text>
            </View>
            <View style={styles.budgetStats}>
              <View style={styles.budgetStat}>
                <Text style={styles.budgetStatNum}>{otSummary.total_ot_hours}h</Text>
                <Text style={styles.budgetStatLabel}>THIS MONTH</Text>
              </View>
              <View style={styles.budgetDivider} />
              <View style={styles.budgetStat}>
                <Text style={[styles.budgetStatNum, { color: otSummary.projected_ot_hours > 80 ? Theme.colors.absent : Theme.colors.text }]}>
                  ~{otSummary.projected_ot_hours}h
                </Text>
                <Text style={styles.budgetStatLabel}>PROJECTED</Text>
              </View>
            </View>
            {otSummary.sites.length > 0 && (
              <View style={styles.budgetSites}>
                {otSummary.sites.slice(0, 3).map((s) => (
                  <View key={s.site_id} style={styles.budgetSiteRow}>
                    <MaterialCommunityIcons
                      name="map-marker-outline"
                      size={12}
                      color={s.ot_hours > 20 ? Theme.colors.absent : Theme.colors.placeholder}
                    />
                    <Text style={[styles.budgetSiteName, s.ot_hours > 20 && { color: Theme.colors.absent }]} numberOfLines={1}>
                      {s.site_name}
                    </Text>
                    <Text style={[styles.budgetSiteHours, s.ot_hours > 20 && { color: Theme.colors.absent, fontWeight: 'bold' }]}>
                      {s.ot_hours}h {s.ot_hours > 20 ? '⚠' : ''}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        ) : null}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(true); }}
            colors={[Theme.colors.primary]}
            tintColor={Theme.colors.primary}
          />
        }
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <Card.Content>
              <View style={styles.header}>
                <View style={styles.guardMeta}>
                  <Text style={styles.name}>{item.guard.name}</Text>
                  <Text style={styles.site}>
                    {item.site_name || '—'} {item.post ? `• ${item.post}` : ''}
                  </Text>
                  {item.date && (
                    <Text style={styles.date}>{item.date}</Text>
                  )}
                </View>
                <View style={styles.hoursChip}>
                  <Text style={styles.hoursNum}>{item.hours}</Text>
                  <Text style={styles.hoursLabel}>hrs OT</Text>
                </View>
              </View>

              {item.shift && (
                <View style={styles.shiftRow}>
                  <MaterialCommunityIcons name="clock-outline" size={13} color={Theme.colors.placeholder} />
                  <Text style={styles.shiftText}>{item.shift}</Text>
                </View>
              )}

              <View style={styles.btns}>
                <Button
                  mode="outlined"
                  onPress={() => { setSelected(item); setNote(''); }}
                  style={styles.btnAuthorize}
                  labelStyle={{ fontSize: 13 }}
                >
                  Review
                </Button>
              </View>
            </Card.Content>
          </Card>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            {errorMsg ? (
              <>
                <MaterialCommunityIcons name="alert-circle-outline" size={48} color={Theme.colors.absent} />
                <Text style={styles.emptyText}>{errorMsg}</Text>
              </>
            ) : (
              <>
                <MaterialCommunityIcons name="clock-check-outline" size={48} color={Theme.colors.present} />
                <Text style={styles.emptyText}>No pending overtime authorizations.</Text>
              </>
            )}
          </View>
        }
      />

      <Portal>
        <Modal
          visible={!!selected}
          onDismiss={() => setSelected(null)}
          contentContainerStyle={styles.modal}
        >
          {selected && (
            <>
              <Text style={styles.modalTitle}>Authorize Overtime</Text>
              <Text style={styles.modalSub}>
                {selected.guard.name} — {selected.hours} hrs at {selected.site_name || 'unknown site'}
              </Text>
              <TextInput
                label="Notes (optional)"
                value={note}
                onChangeText={setNote}
                mode="outlined"
                multiline
                numberOfLines={3}
                style={styles.modalInput}
                outlineColor={Theme.colors.border}
                activeOutlineColor={Theme.colors.primary}
              />
              <View style={styles.modalBtns}>
                <Button
                  mode="outlined"
                  onPress={() => handleAction(false)}
                  disabled={actionLoading}
                  textColor={Theme.colors.absent}
                  style={[styles.modalBtn, { borderColor: Theme.colors.absent }]}
                >
                  Reject
                </Button>
                <Button
                  mode="contained"
                  onPress={() => handleAction(true)}
                  disabled={actionLoading}
                  loading={actionLoading}
                  style={[styles.modalBtn, { backgroundColor: Theme.colors.present }]}
                >
                  Approve
                </Button>
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
  loader: { flex: 1, backgroundColor: Theme.colors.background, justifyContent: 'center', alignItems: 'center' },
  list: { padding: 16, paddingBottom: 32 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderLeftWidth: 4,
    borderLeftColor: Theme.colors.accentGold,
    borderRadius: 14,
    marginBottom: 12,
    elevation: 1,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 },
  guardMeta: { flex: 1, marginRight: 8 },
  name: { fontSize: 16, fontWeight: 'bold', color: Theme.colors.text },
  site: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  date: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  hoursChip: {
    alignItems: 'center',
    backgroundColor: `${Theme.colors.accentGold}14`,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: Theme.colors.accentGold,
  },
  hoursNum: { fontSize: 18, fontWeight: 'bold', color: Theme.colors.accentGold },
  hoursLabel: { fontSize: 9, color: Theme.colors.accentGold, fontWeight: '700' },
  shiftRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 10 },
  shiftText: { fontSize: 12, color: Theme.colors.placeholder },
  btns: { flexDirection: 'row', justifyContent: 'flex-end' },
  btnAuthorize: { borderColor: Theme.colors.primary, borderRadius: 8 },
  empty: { alignItems: 'center', marginTop: 80, gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14, textAlign: 'center' },
  budgetCard: {
    backgroundColor: Theme.colors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    padding: 14,
    marginBottom: 16,
  },
  budgetHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  budgetTitle: { fontSize: 14, fontWeight: 'bold', color: Theme.colors.text, flex: 1 },
  budgetDays: { fontSize: 11, color: Theme.colors.placeholder },
  budgetStats: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  budgetStat: { flex: 1, alignItems: 'center' },
  budgetStatNum: { fontSize: 24, fontWeight: 'bold', color: Theme.colors.text },
  budgetStatLabel: { fontSize: 9, fontWeight: '800', color: Theme.colors.placeholder, letterSpacing: 0.5, marginTop: 2 },
  budgetDivider: { width: 1, height: 40, backgroundColor: Theme.colors.border, marginHorizontal: 8 },
  budgetSites: { gap: 6, borderTopWidth: 1, borderTopColor: Theme.colors.border, paddingTop: 10 },
  budgetSiteRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  budgetSiteName: { flex: 1, fontSize: 12, color: Theme.colors.onSurface },
  budgetSiteHours: { fontSize: 12, color: Theme.colors.placeholder },
  modal: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: 24,
    margin: 20,
  },
  modalTitle: { fontSize: 20, fontWeight: 'bold', color: Theme.colors.text, marginBottom: 4 },
  modalSub: { fontSize: 13, color: Theme.colors.placeholder, marginBottom: 16 },
  modalInput: { backgroundColor: Theme.colors.background, marginBottom: 20 },
  modalBtns: { flexDirection: 'row', gap: 12 },
  modalBtn: { flex: 1, borderRadius: 10 },
});
