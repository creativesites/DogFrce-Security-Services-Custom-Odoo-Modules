import React, { useEffect, useState } from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity } from 'react-native';
import { Text, Modal, Portal, ActivityIndicator, TextInput, Button } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { getIncidentTypes, logIncident, IncidentType } from '../api/supervisor';
import { Theme } from '../theme';

interface Props {
  visible: boolean;
  onClose: () => void;
  onLogged: () => void;
  employeeId: number;
  guardName: string;
}

const SEVERITY_COLOR: Record<string, string> = {
  low: '#10B981',
  medium: Theme.colors.accentGold,
  high: '#F97316',
  critical: '#DC2626',
};

const SEVERITY_ICON: Record<string, string> = {
  low: 'alert-circle-outline',
  medium: 'alert-outline',
  high: 'alert',
  critical: 'alert-octagon',
};

export default function IncidentModal({ visible, onClose, onLogged, employeeId, guardName }: Props) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [types, setTypes] = useState<IncidentType[]>([]);
  const [selectedType, setSelectedType] = useState<IncidentType | null>(null);
  const [note, setNote] = useState('');
  const [step, setStep] = useState<'type' | 'confirm'>('type');

  useEffect(() => {
    if (!visible) return;
    setStep('type');
    setSelectedType(null);
    setNote('');
    setError('');
    setLoading(true);
    getIncidentTypes()
      .then(setTypes)
      .catch((err) => setError(err.message || 'Failed to load incident types'))
      .finally(() => setLoading(false));
  }, [visible]);

  const handleSubmit = async () => {
    if (!selectedType) return;
    setSubmitting(true);
    setError('');
    try {
      await logIncident(employeeId, selectedType.id, note);
      onLogged();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to log incident');
    } finally {
      setSubmitting(false);
    }
  };

  const severityColor = selectedType ? SEVERITY_COLOR[selectedType.severity] : Theme.colors.primary;

  return (
    <Portal>
      <Modal visible={visible} onDismiss={onClose} contentContainerStyle={styles.modal}>
        <View style={styles.modalHeader}>
          <View style={styles.headerLeft}>
            <MaterialCommunityIcons name="shield-alert-outline" size={20} color={Theme.colors.absent} />
            <Text style={styles.modalTitle}>Log Incident</Text>
          </View>
          <TouchableOpacity onPress={onClose} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <MaterialCommunityIcons name="close" size={22} color={Theme.colors.placeholder} />
          </TouchableOpacity>
        </View>

        <View style={styles.guardBanner}>
          <MaterialCommunityIcons name="shield-account" size={14} color={Theme.colors.primary} />
          <Text style={styles.guardName}>{guardName}</Text>
        </View>

        {loading ? (
          <View style={styles.loader}>
            <ActivityIndicator size="large" color={Theme.colors.primary} />
          </View>
        ) : error && !types.length ? (
          <View style={styles.loader}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : step === 'type' ? (
          <>
            <Text style={styles.stepHint}>Select incident type</Text>
            <FlatList
              data={types}
              keyExtractor={(t) => t.id.toString()}
              style={styles.list}
              renderItem={({ item }) => {
                const color = SEVERITY_COLOR[item.severity];
                return (
                  <TouchableOpacity
                    style={[styles.typeItem, selectedType?.id === item.id && { borderColor: color, backgroundColor: `${color}08` }]}
                    onPress={() => { setSelectedType(item); setStep('confirm'); }}
                  >
                    <View style={styles.typeLeft}>
                      <MaterialCommunityIcons
                        name={SEVERITY_ICON[item.severity] as any}
                        size={20}
                        color={color}
                      />
                      <View style={{ marginLeft: 12 }}>
                        <Text style={styles.typeName}>{item.name}</Text>
                        <View style={styles.severityRow}>
                          <View style={[styles.severityDot, { backgroundColor: color }]} />
                          <Text style={[styles.severityLabel, { color }]}>
                            {item.severity.toUpperCase()}
                          </Text>
                          {item.deduction_amount > 0 && (
                            <Text style={styles.deductionHint}>
                              · N${item.deduction_amount.toLocaleString()} deduction
                            </Text>
                          )}
                        </View>
                      </View>
                    </View>
                    <MaterialCommunityIcons name="chevron-right" size={18} color={Theme.colors.placeholder} />
                  </TouchableOpacity>
                );
              }}
              ListEmptyComponent={
                <View style={styles.emptyList}>
                  <Text style={styles.emptyText}>No incident types configured.</Text>
                  <Text style={styles.emptyHint}>Add them in Odoo back-office → Discipline → Incident Types</Text>
                </View>
              }
            />
          </>
        ) : (
          <View style={styles.confirmSection}>
            <View style={[styles.summaryCard, { borderLeftColor: severityColor }]}>
              <View style={styles.summaryRow}>
                <MaterialCommunityIcons name={SEVERITY_ICON[selectedType!.severity] as any} size={18} color={severityColor} />
                <Text style={styles.summaryLabel}>Type</Text>
                <Text style={[styles.summaryValue, { color: severityColor }]}>{selectedType!.name}</Text>
              </View>
              <View style={styles.summaryRow}>
                <MaterialCommunityIcons name="shield-account" size={18} color={Theme.colors.placeholder} />
                <Text style={styles.summaryLabel}>Guard</Text>
                <Text style={styles.summaryValue}>{guardName}</Text>
              </View>
              <View style={styles.summaryRow}>
                <MaterialCommunityIcons name="calendar-today" size={18} color={Theme.colors.placeholder} />
                <Text style={styles.summaryLabel}>Date</Text>
                <Text style={styles.summaryValue}>Today</Text>
              </View>
            </View>

            <TextInput
              label="Notes (optional but recommended)"
              value={note}
              onChangeText={setNote}
              mode="outlined"
              multiline
              numberOfLines={3}
              style={styles.noteInput}
              outlineColor={Theme.colors.border}
              activeOutlineColor={severityColor}
              textColor={Theme.colors.text}
              placeholder="Describe what happened..."
            />

            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            <View style={styles.actionRow}>
              <TouchableOpacity style={styles.backBtn} onPress={() => setStep('type')}>
                <MaterialCommunityIcons name="arrow-left" size={16} color={Theme.colors.placeholder} />
                <Text style={styles.backLabel}>Back</Text>
              </TouchableOpacity>
              <Button
                mode="contained"
                onPress={handleSubmit}
                loading={submitting}
                disabled={submitting}
                style={styles.submitBtn}
                labelStyle={styles.submitBtnLabel}
                buttonColor={severityColor}
                icon="shield-alert"
              >
                Log Incident
              </Button>
            </View>
          </View>
        )}
      </Modal>
    </Portal>
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
  guardBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: `${Theme.colors.primary}0A`,
    borderBottomWidth: 1,
    borderBottomColor: `${Theme.colors.primary}20`,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  guardName: { fontSize: 13, fontWeight: '700', color: Theme.colors.primary },
  loader: { height: 160, justifyContent: 'center', alignItems: 'center' },
  stepHint: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    fontWeight: '600',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  list: { maxHeight: 340, paddingHorizontal: 12, paddingBottom: 8 },
  typeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 12,
    marginBottom: 6,
    marginTop: 4,
    borderRadius: 12,
    backgroundColor: Theme.colors.background,
    borderWidth: 1,
    borderColor: Theme.colors.border,
  },
  typeLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  typeName: { fontSize: 14, fontWeight: '600', color: Theme.colors.text },
  severityRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 3 },
  severityDot: { width: 6, height: 6, borderRadius: 3 },
  severityLabel: { fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  deductionHint: { fontSize: 10, color: Theme.colors.placeholder },
  emptyList: { alignItems: 'center', paddingVertical: 32, gap: 6 },
  emptyText: { fontSize: 13, color: Theme.colors.placeholder, textAlign: 'center' },
  emptyHint: { fontSize: 11, color: Theme.colors.border, textAlign: 'center' },
  confirmSection: { padding: 16, gap: 14 },
  summaryCard: {
    backgroundColor: Theme.colors.background,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    borderLeftWidth: 4,
    padding: 16,
    gap: 12,
  },
  summaryRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  summaryLabel: { fontSize: 12, color: Theme.colors.placeholder, width: 44 },
  summaryValue: { fontSize: 14, fontWeight: '600', color: Theme.colors.text, flex: 1 },
  noteInput: {
    backgroundColor: 'transparent',
    fontSize: 14,
  },
  actionRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  backLabel: { fontSize: 13, color: Theme.colors.placeholder, fontWeight: '600' },
  submitBtn: { flex: 1, borderRadius: 14 },
  submitBtnLabel: { fontSize: 14, fontWeight: 'bold' },
  errorText: { color: Theme.colors.absent, fontSize: 13, textAlign: 'center' },
});
