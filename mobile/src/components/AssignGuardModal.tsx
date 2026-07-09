import React, { useEffect, useState } from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity, Switch } from 'react-native';
import { Text, Modal, Portal, ActivityIndicator, Searchbar, Button } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import {
  getAssignableData,
  assignGuard,
  AssignableData,
  AssignableGuard,
  AssignablePost,
  AssignableShift,
} from '../api/supervisor';
import { Theme } from '../theme';

interface Props {
  siteId: number;
  visible: boolean;
  onClose: () => void;
  onAssigned: () => void;
}

type Step = 'guard' | 'post' | 'shift' | 'confirm';

export default function AssignGuardModal({ siteId, visible, onClose, onAssigned }: Props) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<AssignableData | null>(null);

  const [step, setStep] = useState<Step>('guard');
  const [search, setSearch] = useState('');
  const [selectedGuard, setSelectedGuard] = useState<AssignableGuard | null>(null);
  const [selectedPost, setSelectedPost] = useState<AssignablePost | null>(null);
  const [selectedShift, setSelectedShift] = useState<AssignableShift | null>(null);
  const [markPresent, setMarkPresent] = useState(true);

  useEffect(() => {
    if (!visible) return;
    setStep('guard');
    setSelectedGuard(null);
    setSelectedPost(null);
    setSelectedShift(null);
    setMarkPresent(true);
    setSearch('');
    setError('');
    setLoading(true);
    getAssignableData(siteId)
      .then(setData)
      .catch((err) => setError(err.message || 'Failed to load data'))
      .finally(() => setLoading(false));
  }, [visible, siteId]);

  const handleAssign = async () => {
    if (!selectedGuard || !selectedPost || !selectedShift) return;
    setSubmitting(true);
    setError('');
    try {
      await assignGuard(siteId, selectedGuard.id, selectedPost.id, selectedShift.id, markPresent);
      onAssigned();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to assign guard');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredGuards = (data?.guards || []).filter((g) =>
    g.name.toLowerCase().includes(search.toLowerCase())
  );

  const renderHeader = () => {
    const steps: { key: Step; label: string; value: string | null }[] = [
      { key: 'guard', label: 'Guard', value: selectedGuard?.name ?? null },
      { key: 'post', label: 'Post', value: selectedPost?.name ?? null },
      { key: 'shift', label: 'Shift', value: selectedShift?.name ?? null },
    ];
    return (
      <View style={styles.stepRow}>
        {steps.map((s, i) => (
          <React.Fragment key={s.key}>
            <TouchableOpacity
              style={[styles.stepChip, step === s.key && styles.stepChipActive]}
              onPress={() => s.value && setStep(s.key)}
              disabled={!s.value && step !== s.key}
            >
              <Text style={[styles.stepLabel, step === s.key && styles.stepLabelActive]}>
                {s.value ?? s.label}
              </Text>
            </TouchableOpacity>
            {i < steps.length - 1 && (
              <MaterialCommunityIcons
                name="chevron-right"
                size={16}
                color={Theme.colors.border}
                style={{ alignSelf: 'center' }}
              />
            )}
          </React.Fragment>
        ))}
      </View>
    );
  };

  const renderGuardStep = () => (
    <>
      <Searchbar
        placeholder="Search guards..."
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
            onPress={() => {
              setSelectedGuard(item);
              setStep('post');
              setSearch('');
            }}
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
                ? 'All guards are already assigned to this site today.'
                : 'No guards match your search.'}
            </Text>
          </View>
        }
      />
    </>
  );

  const renderPostStep = () => (
    <FlatList
      data={data?.posts ?? []}
      keyExtractor={(p) => p.id.toString()}
      style={styles.list}
      renderItem={({ item }) => (
        <TouchableOpacity
          style={[styles.listItem, selectedPost?.id === item.id && styles.listItemSelected]}
          onPress={() => {
            setSelectedPost(item);
            setStep('shift');
          }}
        >
          <View style={styles.listItemLeft}>
            <MaterialCommunityIcons name="map-marker-outline" size={22} color={Theme.colors.accentCyan} />
            <Text style={[styles.listItemName, { marginLeft: 12 }]}>{item.name}</Text>
          </View>
          {selectedPost?.id === item.id && (
            <MaterialCommunityIcons name="check-circle" size={20} color={Theme.colors.present} />
          )}
        </TouchableOpacity>
      )}
      ListEmptyComponent={
        <View style={styles.emptyList}>
          <Text style={styles.emptyText}>No posts configured for this site.</Text>
          <Text style={styles.emptyHint}>Add posts via the Odoo back-office first.</Text>
        </View>
      }
    />
  );

  const renderShiftStep = () => (
    <FlatList
      data={data?.shifts ?? []}
      keyExtractor={(s) => s.id.toString()}
      style={styles.list}
      renderItem={({ item }) => {
        const toHHMM = (h: number) => {
          const hh = Math.floor(h).toString().padStart(2, '0');
          const mm = Math.round((h % 1) * 60).toString().padStart(2, '0');
          return `${hh}:${mm}`;
        };
        return (
          <TouchableOpacity
            style={[styles.listItem, selectedShift?.id === item.id && styles.listItemSelected]}
            onPress={() => {
              setSelectedShift(item);
              setStep('confirm');
            }}
          >
            <View style={styles.listItemLeft}>
              <MaterialCommunityIcons name="clock-outline" size={22} color={Theme.colors.accentGold} />
              <View style={{ marginLeft: 12 }}>
                <Text style={styles.listItemName}>{item.name}</Text>
                <Text style={styles.listItemSub}>
                  {toHHMM(item.start_hour)} – {toHHMM(item.end_hour)} · {item.duration_hours}h
                </Text>
              </View>
            </View>
            {selectedShift?.id === item.id && (
              <MaterialCommunityIcons name="check-circle" size={20} color={Theme.colors.present} />
            )}
          </TouchableOpacity>
        );
      }}
      ListEmptyComponent={
        <View style={styles.emptyList}>
          <Text style={styles.emptyText}>No shift templates found.</Text>
        </View>
      }
    />
  );

  const renderConfirmStep = () => (
    <View style={styles.confirmSection}>
      <View style={styles.summaryCard}>
        <SummaryRow icon="shield-account" label="Guard" value={selectedGuard!.name} />
        <SummaryRow icon="map-marker-outline" label="Post" value={selectedPost!.name} />
        <SummaryRow icon="clock-outline" label="Shift" value={selectedShift!.name} />
      </View>

      <View style={styles.toggleRow}>
        <View style={styles.toggleLeft}>
          <MaterialCommunityIcons name="check-circle-outline" size={22} color={Theme.colors.present} />
          <View style={{ marginLeft: 12 }}>
            <Text style={styles.toggleLabel}>Mark as Present now</Text>
            <Text style={styles.toggleHint}>Check-in time will be set to right now</Text>
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

      <Button
        mode="contained"
        onPress={handleAssign}
        loading={submitting}
        disabled={submitting}
        style={styles.assignBtn}
        labelStyle={styles.assignBtnLabel}
        icon={markPresent ? 'check-circle' : 'account-plus'}
      >
        {markPresent ? 'Assign & Mark Present' : 'Add to Roster'}
      </Button>
    </View>
  );

  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onClose}
        contentContainerStyle={styles.modal}
      >
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Assign Guard</Text>
          <TouchableOpacity onPress={onClose} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <MaterialCommunityIcons name="close" size={22} color={Theme.colors.placeholder} />
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={styles.loader}>
            <ActivityIndicator size="large" color={Theme.colors.primary} />
          </View>
        ) : error && !data ? (
          <View style={styles.loader}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : (
          <>
            {renderHeader()}
            <View style={styles.stepContent}>
              {step === 'guard' && renderGuardStep()}
              {step === 'post' && renderPostStep()}
              {step === 'shift' && renderShiftStep()}
              {step === 'confirm' && renderConfirmStep()}
            </View>
          </>
        )}
      </Modal>
    </Portal>
  );
}

function SummaryRow({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <View style={styles.summaryRow}>
      <MaterialCommunityIcons name={icon as any} size={18} color={Theme.colors.placeholder} />
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={styles.summaryValue}>{value}</Text>
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
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: Theme.colors.text,
  },
  loader: {
    height: 160,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 4,
  },
  stepChip: {
    flex: 1,
    paddingVertical: 6,
    paddingHorizontal: 8,
    borderRadius: 8,
    backgroundColor: Theme.colors.surfaceVariant,
    alignItems: 'center',
  },
  stepChipActive: {
    backgroundColor: `${Theme.colors.primary}14`,
    borderColor: Theme.colors.primary,
    borderWidth: 1,
  },
  stepLabel: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    fontWeight: '600',
    textAlign: 'center',
  },
  stepLabelActive: {
    color: Theme.colors.primary,
  },
  stepContent: {
    minHeight: 400,
    flexShrink: 1,
  },
  search: {
    margin: 12,
    marginTop: 4,
    backgroundColor: Theme.colors.background,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    elevation: 0,
  },
  list: {
    maxHeight: 320,
    paddingHorizontal: 12,
  },
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
  listItemSelected: {
    borderColor: Theme.colors.present,
    backgroundColor: `${Theme.colors.present}08`,
  },
  listItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  listItemName: {
    fontSize: 14,
    fontWeight: '600',
    color: Theme.colors.text,
  },
  listItemSub: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    marginTop: 2,
  },
  emptyList: {
    alignItems: 'center',
    paddingVertical: 32,
    gap: 8,
  },
  emptyText: {
    fontSize: 13,
    color: Theme.colors.placeholder,
    textAlign: 'center',
  },
  emptyHint: {
    fontSize: 11,
    color: Theme.colors.border,
    textAlign: 'center',
  },
  confirmSection: {
    padding: 16,
    gap: 16,
  },
  summaryCard: {
    backgroundColor: Theme.colors.background,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    padding: 16,
    gap: 12,
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  summaryLabel: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    width: 44,
  },
  summaryValue: {
    fontSize: 14,
    fontWeight: '600',
    color: Theme.colors.text,
    flex: 1,
  },
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
  toggleLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  toggleLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: Theme.colors.text,
  },
  toggleHint: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    marginTop: 2,
  },
  errorText: {
    color: Theme.colors.absent,
    fontSize: 13,
    textAlign: 'center',
  },
  assignBtn: {
    borderRadius: 14,
    paddingVertical: 4,
  },
  assignBtnLabel: {
    fontSize: 15,
    fontWeight: 'bold',
  },
});
