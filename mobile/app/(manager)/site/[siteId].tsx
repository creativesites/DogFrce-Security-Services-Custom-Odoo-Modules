import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, ScrollView, RefreshControl } from 'react-native';
import { Text, Button, Card, ActivityIndicator, Portal, Modal, TextInput } from 'react-native-paper';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getSiteDetails, approveOvertime, SiteDetailResponse } from '../../../src/api/manager';
import { useAppStore } from '../../../src/stores/appStore';
import { Theme } from '../../../src/theme';
import GuardCard from '../../../src/components/GuardCard';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function SiteDetailScreen() {
  const { siteId } = useLocalSearchParams();
  const [data, setData] = useState<SiteDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Overtime modal states
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [approveNote, setApproveNote] = useState('');

  const { selectedDate, refreshTrigger, triggerRefresh } = useAppStore();
  const router = useRouter();

  const loadDetails = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await getSiteDetails(Number(siteId), selectedDate);
      setData(res);
    } catch (err) {
      console.error('Failed to load site details', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDetails();
  }, [siteId, selectedDate, refreshTrigger]);

  const onRefresh = () => {
    setRefreshing(true);
    loadDetails(true);
  };

  const handleOvertimeAction = async (approved: boolean) => {
    if (!selectedRecordId) return;
    setActionLoading(true);
    try {
      await approveOvertime(selectedRecordId, approved, approveNote);
      setModalVisible(false);
      setApproveNote('');
      triggerRefresh();
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

  if (!data) {
    return (
      <View style={styles.loader}>
        <Text style={styles.errorText}>Site data not found.</Text>
        <Button mode="contained" onPress={() => router.back()} style={styles.backBtn}>
          Go Back
        </Button>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
        contentContainerStyle={styles.scroll}
      >
        <Card style={styles.metaCard}>
          <Card.Content>
            <Text style={styles.siteTitle}>{data.site.name}</Text>
            <Text style={styles.clientSubtitle}>{data.site.client}</Text>
            
            <View style={styles.metaDivider} />
            
            <View style={styles.metaRows}>
              <View style={styles.metaRow}>
                <MaterialCommunityIcons name="account-tie" size={16} color={Theme.colors.placeholder} />
                <Text style={styles.metaLabel}>Supervisor: {data.supervisor || 'Unassigned'}</Text>
              </View>
              <View style={styles.metaRow}>
                <MaterialCommunityIcons name="list-status" size={16} color={Theme.colors.placeholder} />
                <Text style={styles.metaLabel}>Batch State: {data.batch_state.toUpperCase()}</Text>
              </View>
            </View>
          </Card.Content>
        </Card>

        {/* Overtime Pending Panel */}
        {data.overtime_pending && data.overtime_pending.length > 0 ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Pending Overtime Authorization</Text>
            {data.overtime_pending.map((item) => (
              <Card key={item.record_id} style={styles.otCard}>
                <Card.Content>
                  <View style={styles.otHeader}>
                    <Text style={styles.otGuardName}>{item.guard.name}</Text>
                    <Text style={styles.otHours}>{item.overtime_hours} hrs requested</Text>
                  </View>
                  <Text style={styles.otDetails}>
                    Post: {item.post} | Shift: {item.shift}
                  </Text>
                  <View style={styles.otActions}>
                    <Button
                      mode="contained"
                      onPress={() => {
                        setSelectedRecordId(item.record_id);
                        setModalVisible(true);
                      }}
                      style={styles.actionApprove}
                      labelStyle={styles.actionBtnLabel}
                    >
                      Authorize
                    </Button>
                  </View>
                </Card.Content>
              </Card>
            ))}
          </View>
        ) : null}

        {/* Regular Roster list */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Roster Attendance list</Text>
          {data.roster && data.roster.length > 0 ? (
            data.roster.map((item, idx) => (
              <GuardCard
                key={item.record_id || item.slot_id || idx}
                name={item.guard.name}
                grade={item.guard.grade}
                post={item.post}
                shift={item.shift}
                status={item.manual_presence}
                checkIn={item.check_in}
                checkOut={item.check_out}
              />
            ))
          ) : (
            <View style={styles.empty}>
              <MaterialCommunityIcons name="clipboard-alert-outline" size={32} color={Theme.colors.placeholder} />
              <Text style={styles.emptyText}>No roster slots active today.</Text>
            </View>
          )}
        </View>
      </ScrollView>

      {/* Overtime Approval Modal */}
      <Portal>
        <Modal
          visible={modalVisible}
          onDismiss={() => setModalVisible(false)}
          contentContainerStyle={styles.modal}
        >
          <Text style={styles.modalTitle}>Authorize Overtime</Text>
          <Text style={styles.modalSub}>
            Approve or reject the overtime hours logged by this guard.
          </Text>

          <TextInput
            label="Approver / Rejection Notes"
            value={approveNote}
            onChangeText={setApproveNote}
            mode="outlined"
            multiline
            numberOfLines={3}
            style={styles.modalInput}
            outlineColor={Theme.colors.border}
            activeOutlineColor={Theme.colors.primary}
            textColor={Theme.colors.text}
          />

          <View style={styles.modalBtns}>
            <Button
              mode="outlined"
              onPress={() => handleOvertimeAction(false)}
              disabled={actionLoading}
              borderColor={Theme.colors.absent}
              textColor={Theme.colors.absent}
              style={styles.modalBtn}
            >
              Reject
            </Button>
            <Button
              mode="contained"
              onPress={() => handleOvertimeAction(true)}
              disabled={actionLoading}
              loading={actionLoading}
              style={[styles.modalBtn, { backgroundColor: Theme.colors.present }]}
            >
              Approve
            </Button>
          </View>
        </Modal>
      </Portal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0B0F',
  },
  scroll: {
    padding: 16,
  },
  loader: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    justifyContent: 'center',
    alignItems: 'center',
  },
  metaCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 20,
    marginBottom: 20,
  },
  siteTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFF',
  },
  clientSubtitle: {
    fontSize: 14,
    color: Theme.colors.placeholder,
    marginTop: 2,
  },
  metaDivider: {
    height: 1,
    backgroundColor: Theme.colors.border,
    marginVertical: 14,
  },
  metaRows: {
    gap: 8,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  metaLabel: {
    color: Theme.colors.onSurface,
    fontSize: 13,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 12,
  },
  otCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: Theme.colors.accentGold,
  },
  otHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  otGuardName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFF',
  },
  otHours: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Theme.colors.accentGold,
  },
  otDetails: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    marginTop: 4,
  },
  otActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 12,
  },
  actionApprove: {
    backgroundColor: Theme.colors.primary,
    borderRadius: 8,
  },
  actionBtnLabel: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  empty: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyText: {
    color: Theme.colors.placeholder,
    fontSize: 13,
    marginTop: 8,
  },
  modal: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: 24,
    margin: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
  },
  modalSub: {
    fontSize: 13,
    color: Theme.colors.placeholder,
    marginTop: 4,
    marginBottom: 16,
  },
  modalInput: {
    backgroundColor: 'transparent',
    marginBottom: 20,
  },
  modalBtns: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
  },
  modalBtn: {
    borderRadius: 10,
    flex: 1,
  },
  errorText: {
    color: Theme.colors.absent,
    marginBottom: 16,
  },
  backBtn: {
    borderRadius: 12,
  },
});
