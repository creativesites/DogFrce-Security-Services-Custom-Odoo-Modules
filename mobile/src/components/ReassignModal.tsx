import React, { useEffect, useState } from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity, Switch } from 'react-native';
import { Text, Modal, Portal, ActivityIndicator, Searchbar, Button } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import {
  getAssignableData,
  reassignGuard,
  AssignableData,
  AssignableGuard,
} from '../api/supervisor';
import { Theme } from '../theme';

interface Props {
  siteId: number;
  visible: boolean;
  onClose: () => void;
  onReassigned: () => void;
  recordId: number;
  releasedGuardName: string;
  postId: number;
  postName: string;
  shiftTemplateId: number;
  shiftName: string;
}

export default function ReassignModal({
  siteId,
  visible,
  onClose,
  onReassigned,
  recordId,
  releasedGuardName,
  postId,
  postName,
  shiftTemplateId,
  shiftName,
}: Props) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<AssignableData | null>(null);
  const [search, setSearch] = useState('');
  const [selectedGuard, setSelectedGuard] = useState<AssignableGuard | null>(null);
  const [markPresent, setMarkPresent] = useState(true);
  const [step, setStep] = useState<'guard' | 'confirm'>('guard');

  useEffect(() => {
    if (!visible) return;
    setStep('guard');
    setSelectedGuard(null);
    setMarkPresent(true);
    setSearch('');
    setError('');
    setLoading(true);
    getAssignableData(siteId)
      .then(setData)
      .catch((err) => setError(err.message || 'Failed to load guards'))
      .finally(() => setLoading(false));
  }, [visible, siteId]);

  const handleReassign = async () => {
    if (!selectedGuard) return;
    setSubmitting(true);
    setError('');
    try {
      await reassignGuard(siteId, recordId, selectedGuard.id, postId, shiftTemplateId, markPresent);
      onReassigned();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to reassign guard');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredGuards = (data?.guards || []).filter((g) =>
    g.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Portal>
      <Modal visible={visible} onDismiss={onClose} contentContainerStyle={styles.modal}>
        <View style={styles.modalHeader}>
          <View style={styles.headerLeft}>
            <MaterialCommunityIcons name="account-switch-outline" size={20} color="#DC2626" />
            <Text style={styles.modalTitle}>Emergency Reassign</Text>
          </View>
          <TouchableOpacity onPress={onClose} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <MaterialCommunityIcons name="close" size={22} color={Theme.colors.placeholder} />
          </TouchableOpacity>
        </View>

        <View style={styles.warningBanner}>
          <MaterialCommunityIcons name="alert-outline" size={14} color="#DC2626" />
          <Text style={styles.warningText}>
            <Text style={styles.warningName}>{releasedGuardName}</Text>
            {' '}will be marked absent. This action is permanent.
          </Text>
        </View>

        {loading ? (
          <View style={styles.loader}>
            <ActivityIndicator size="large" color={Theme.colors.primary} />
          </View>
        ) : error && !data ? (
          <View style={styles.loader}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : step === 'guard' ? (
          <>
            <View style={styles.contextRow}>
              <View style={styles.contextChip}>
                <MaterialCommunityIcons name="map-marker-outline" size={13} color={Theme.colors.accentCyan} />
                <Text style={styles.contextChipText}>{postName}</Text>
              </View>
              <View style={styles.contextChip}>
                <MaterialCommunityIcons name="clock-outline" size={13} color={Theme.colors.accentGold} />
                <Text style={styles.contextChipText}>{shiftName}</Text>
              </View>
            </View>

            <Searchbar
              placeholder="Search available guards..."
              value={search}
              onChangeText={setSearch}
              style={styles.search}
              inputStyle={{ fontSize: 14, color: Theme.colors.text }}
              placeholderTextColor={Theme.colors.placeholder}
              iconColor={Theme.colors.primary}
            />

            <FlatList
              data={filteredGuards}
              keyExtractor={(g) => g.id.toString()}
              style={styles.list}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.listItem}
                  onPress={() => { setSelectedGuard(item); setStep('confirm'); }}
                >
                  <View style={styles.listItemLeft}>
                    <MaterialCommunityIcons name="shield-account" size={22} color={Theme.colors.primary} />
                    <View style={{ marginLeft: 12 }}>
                      <Text style={styles.listItemName}>{item.name}</Text>
                      {item.grade && <Text style={styles.listItemSub}>{item.grade}</Text>}
                    </View>
                  </View>
                  <MaterialCommunityIcons name="chevron-right" size={18} color={Theme.colors.placeholder} />
                </TouchableOpacity>
              )}
              ListEmptyComponent={
                <View style={styles.emptyList}>
                  <Text style={styles.emptyText}>
                    {data?.guards.length === 0
                      ? 'All available guards are already assigned today.'
                      : 'No guards match your search.'}
                  </Text>
                </View>
              }
            />
          </>
        ) : (
          <View style={styles.confirmSection}>
            <View style={styles.summaryCard}>
              <SummaryRow icon="account-remove" label="Releasing" value={releasedGuardName} valueColor="#DC2626" />
              <SummaryRow icon="account-plus" label="Replacing" value={selectedGuard!.name} valueColor={Theme.colors.present} />
              <SummaryRow icon="map-marker-outline" label="Post" value={postName} />
              <SummaryRow icon="clock-outline" label="Shift" value={shiftName} />
            </View>

            <View style={styles.toggleRow}>
              <View style={styles.toggleLeft}>
                <MaterialCommunityIcons name="check-circle-outline" size={22} color={Theme.colors.present} />
                <View style={{ marginLeft: 12 }}>
                  <Text style={styles.toggleLabel}>Mark replacement as Present</Text>
                  <Text style={styles.toggleHint}>Check-in time set to right now</Text>
                </View>
              </View>
              <Switch
                value={markPresent}
                onValueChange={setMarkPresent}
                trackColor={{ true: Theme.colors.present, false: Theme.colors.border }}
                thumbColor="#FFF"
              />
            </View>

            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            <View style={styles.actionRow}>
              <TouchableOpacity style={styles.backBtn} onPress={() => setStep('guard')}>
                <MaterialCommunityIcons name="arrow-left" size={16} color={Theme.colors.placeholder} />
                <Text style={styles.backLabel}>Back</Text>
              </TouchableOpacity>
              <Button
                mode="contained"
                onPress={handleReassign}
                loading={submitting}
                disabled={submitting}
                style={styles.reassignBtn}
                labelStyle={styles.reassignBtnLabel}
                buttonColor="#DC2626"
                icon="account-switch-outline"
              >
                Confirm Reassignment
              </Button>
            </View>
          </View>
        )}
      </Modal>
    </Portal>
  );
}

function SummaryRow({
  icon,
  label,
  value,
  valueColor,
}: {
  icon: string;
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <View style={styles.summaryRow}>
      <MaterialCommunityIcons name={icon as any} size={18} color={Theme.colors.placeholder} />
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={[styles.summaryValue, valueColor ? { color: valueColor } : {}]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  modal: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 24,
    margin: 16,
    maxHeight: '85%',
    overflow: 'hidden',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: Theme.colors.border,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  modalTitle: { fontSize: 17, fontWeight: 'bold', color: Theme.colors.text },
  warningBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: '#FEF2F2',
    borderBottomWidth: 1,
    borderBottomColor: '#FECACA',
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  warningText: { fontSize: 12, color: '#7F1D1D', flex: 1, lineHeight: 18 },
  warningName: { fontWeight: '700' },
  loader: { height: 160, justifyContent: 'center', alignItems: 'center' },
  contextRow: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingTop: 12,
  },
  contextChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Theme.colors.surfaceVariant,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  contextChipText: { fontSize: 11, color: Theme.colors.onSurface, fontWeight: '600' },
  search: {
    margin: 12,
    marginTop: 8,
    backgroundColor: Theme.colors.background,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    elevation: 0,
  },
  list: { maxHeight: 300, paddingHorizontal: 12 },
  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 12,
    marginBottom: 6,
    borderRadius: 12,
    backgroundColor: Theme.colors.background,
    borderWidth: 1,
    borderColor: Theme.colors.border,
  },
  listItemLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  listItemName: { fontSize: 14, fontWeight: '600', color: Theme.colors.text },
  listItemSub: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  emptyList: { alignItems: 'center', paddingVertical: 32 },
  emptyText: { fontSize: 13, color: Theme.colors.placeholder, textAlign: 'center' },
  confirmSection: { padding: 16, gap: 14 },
  summaryCard: {
    backgroundColor: Theme.colors.background,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    padding: 16,
    gap: 12,
  },
  summaryRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  summaryLabel: { fontSize: 12, color: Theme.colors.placeholder, width: 60 },
  summaryValue: { fontSize: 14, fontWeight: '600', color: Theme.colors.text, flex: 1 },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Theme.colors.background,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    padding: 14,
  },
  toggleLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  toggleLabel: { fontSize: 14, fontWeight: '600', color: Theme.colors.text },
  toggleHint: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  actionRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  backLabel: { fontSize: 13, color: Theme.colors.placeholder, fontWeight: '600' },
  reassignBtn: { flex: 1, borderRadius: 14 },
  reassignBtnLabel: { fontSize: 14, fontWeight: 'bold' },
  errorText: { color: Theme.colors.absent, fontSize: 13, textAlign: 'center' },
});
