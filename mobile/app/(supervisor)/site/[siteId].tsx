import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Text, Searchbar, Button, FAB, ActivityIndicator } from 'react-native-paper';
import { getSitePostingSheet, SitePostingSheetResponse, submitBatch, markPresence, AttendanceRecord, bulkMarkPresent } from '../../../src/api/supervisor';
import { useAppStore } from '../../../src/stores/appStore';
import { Theme } from '../../../src/theme';
import GuardCard from '../../../src/components/GuardCard';
import AssignGuardModal from '../../../src/components/AssignGuardModal';
import ReassignModal from '../../../src/components/ReassignModal';
import IncidentModal from '../../../src/components/IncidentModal';
import GuardProfileModal from '../../../src/components/GuardProfileModal';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { flushQueue, getQueue, getQueuedRecordIds } from '../../../src/utils/offlineQueue';
import { isOffline } from '../../../src/api/client';
import { generatePostingSheetPDF } from '../../../src/utils/pdfExport';

export default function SitePostingSheetScreen() {
  const { siteId } = useLocalSearchParams<{ siteId: string }>();
  const [data, setData] = useState<(SitePostingSheetResponse & { _cached?: boolean; _cachedAt?: number }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [search, setSearch] = useState('');
  const [pendingCount, setPendingCount] = useState(0);
  const [assignModalVisible, setAssignModalVisible] = useState(false);
  const [reassignTarget, setReassignTarget] = useState<AttendanceRecord | null>(null);
  const [incidentTarget, setIncidentTarget] = useState<AttendanceRecord | null>(null);
  const [profileTarget, setProfileTarget] = useState<{ id: number; name: string } | null>(null);
  const [bulkMarking, setBulkMarking] = useState(false);
  const [exportingPDF, setExportingPDF] = useState(false);
  const [queuedIds, setQueuedIds] = useState<Set<number>>(new Set());

  const { refreshTrigger, triggerRefresh } = useAppStore();
  const router = useRouter();

  const loadData = async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getSitePostingSheet(Number(siteId));
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load posting sheet.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    getQueue().then(q => setPendingCount(q.length));
    getQueuedRecordIds().then(ids => setQueuedIds(new Set(ids)));
  }, [siteId, refreshTrigger]);

  const handleFlushQueue = async () => {
    await flushQueue();
    setPendingCount(0);
    setQueuedIds(new Set());
    triggerRefresh();
  };

  const handleBulkMark = async () => {
    setBulkMarking(true);
    try {
      const result = await bulkMarkPresent(Number(siteId));
      if (result.updated > 0) triggerRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to bulk-mark guards.');
    } finally {
      setBulkMarking(false);
    }
  };

  const handleSubmit = async () => {
    if (!data?.batch_id) return;
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

  const filteredSlots = (data?.slots || []).filter(s =>
    s.guard.name.toLowerCase().includes(search.toLowerCase())
  );
  const filteredFallback = (data?.roster_slots || []).filter(s =>
    s.guard.name.toLowerCase().includes(search.toLowerCase())
  );

  const isAllMarked = data?.slots && data.slots.length > 0 &&
    data.slots.every(s => s.manual_presence !== 'not_marked');

  const siteName = data?.site?.name || `Site ${siteId}`;
  const batchState = data?.batch_state;

  const handleExportPDF = async () => {
    if (!data) return;
    setExportingPDF(true);
    try {
      await generatePostingSheetPDF(data, siteName);
    } catch (err: any) {
      alert('Failed to generate PDF: ' + (err.message || 'Unknown error'));
    } finally {
      setExportingPDF(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerBar}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <MaterialCommunityIcons name="arrow-left" size={22} color={Theme.colors.text} />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.siteName} numberOfLines={1}>{siteName}</Text>
          <Text style={styles.clientName}>{data?.client?.name || ''}</Text>
        </View>
        <TouchableOpacity onPress={handleExportPDF} disabled={exportingPDF || !data} style={styles.pdfBtn}>
          {exportingPDF ? (
            <ActivityIndicator size={16} color={Theme.colors.primary} />
          ) : (
            <MaterialCommunityIcons name="file-pdf-box" size={22} color={Theme.colors.primary} />
          )}
        </TouchableOpacity>
        {batchState && (
          <View style={[styles.stateChip, batchState === 'captured' && styles.capturedChip]}>
            <Text style={styles.stateChipText}>{batchState.toUpperCase()}</Text>
          </View>
        )}
        {data?._cached && (
          <View style={styles.cachedChip}>
            <MaterialCommunityIcons name="database-clock-outline" size={11} color={Theme.colors.accentGold} />
          </View>
        )}
      </View>

      <Searchbar
        placeholder="Filter guards..."
        value={search}
        onChangeText={setSearch}
        style={styles.search}
        inputStyle={{ fontSize: 14, color: Theme.colors.text }}
        placeholderTextColor={Theme.colors.placeholder}
        iconColor={Theme.colors.primary}
      />

      {pendingCount > 0 && (
        <TouchableOpacity style={styles.syncChip} onPress={handleFlushQueue}>
          <MaterialCommunityIcons name="cloud-upload-outline" size={16} color="#fff" />
          <Text style={styles.syncChipText}>Sync {pendingCount} pending mark{pendingCount !== 1 ? 's' : ''}</Text>
        </TouchableOpacity>
      )}

      {data?.slots && data.slots.some(s => s.manual_presence === 'not_marked') && (
        <TouchableOpacity
          style={styles.bulkMarkChip}
          onPress={handleBulkMark}
          disabled={bulkMarking}
          activeOpacity={0.75}
        >
          <MaterialCommunityIcons name="check-all" size={16} color="#fff" />
          <Text style={styles.syncChipText}>
            {bulkMarking ? 'Marking...' : 'Mark All Not-Marked as Present'}
          </Text>
        </TouchableOpacity>
      )}

      {errorMsg ? (
        <View style={styles.errBox}>
          <MaterialCommunityIcons name="alert-circle-outline" size={24} color={Theme.colors.absent} />
          <Text style={styles.errText}>{errorMsg}</Text>
          <Button onPress={() => loadData()} mode="outlined" style={styles.errBtn}>Retry</Button>
        </View>
      ) : null}

      {!errorMsg && data?.slots ? (
        <FlatList
          data={filteredSlots}
          keyExtractor={(item) => item.record_id.toString()}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); loadData(true); }}
              colors={[Theme.colors.primary]}
              tintColor={Theme.colors.primary}
            />
          }
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <GuardCard
              name={item.guard.name}
              grade={item.guard.grade}
              post={item.post}
              shift={item.shift}
              status={queuedIds.has(item.record_id) ? 'queued' : item.manual_presence}
              checkIn={item.check_in}
              checkOut={item.check_out}
              onPress={() => router.push({
                pathname: '/(supervisor)/mark/[recordId]',
                params: { recordId: item.record_id.toString(), siteId: siteId },
              })}
              onProfile={() => setProfileTarget({ id: item.guard.id, name: item.guard.name })}
              onReassign={
                (item.manual_presence === 'awol' || item.manual_presence === 'absent')
                  ? () => setReassignTarget(item)
                  : undefined
              }
              onIncident={() => setIncidentTarget(item)}
            />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <MaterialCommunityIcons name="shield-off-outline" size={48} color={Theme.colors.placeholder} />
              <Text style={styles.emptyText}>No guards matching filter.</Text>
            </View>
          }
        />
      ) : null}

      {!errorMsg && data?.roster_slots && !data.slots ? (
        <FlatList
          data={filteredFallback}
          keyExtractor={(item) => item.slot_id.toString()}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); loadData(true); }}
              colors={[Theme.colors.primary]}
              tintColor={Theme.colors.primary}
            />
          }
          contentContainerStyle={styles.list}
          ListHeaderComponent={
            <View style={styles.noShiftBanner}>
              <MaterialCommunityIcons name="information-outline" size={16} color={Theme.colors.scheduled} />
              <Text style={styles.noShiftText}>Shift not started yet — showing scheduled roster</Text>
            </View>
          }
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

      {/* Add Guard FAB — visible whenever posting sheet is in draft (or no batch yet) */}
      {(!batchState || batchState === 'draft') && (
        <FAB
          icon="account-plus"
          style={[styles.fab, styles.fabAdd, (data?.batch_id && batchState === 'draft' && isAllMarked) ? styles.fabAddShifted : undefined]}
          onPress={() => setAssignModalVisible(true)}
          color="#FFF"
          size="medium"
        />
      )}

      {/* Submit FAB — only when all guards are marked */}
      {data?.batch_id && batchState === 'draft' && isAllMarked && (
        <FAB
          icon="check-all"
          label={submitting ? 'Submitting...' : 'Submit Posting Sheet'}
          style={styles.fab}
          onPress={handleSubmit}
          loading={submitting}
          color="#FFF"
        />
      )}

      <AssignGuardModal
        siteId={Number(siteId)}
        visible={assignModalVisible}
        onClose={() => setAssignModalVisible(false)}
        onAssigned={() => triggerRefresh()}
      />

      {reassignTarget && reassignTarget.post_id && reassignTarget.shift_template_id && (
        <ReassignModal
          siteId={Number(siteId)}
          visible={!!reassignTarget}
          onClose={() => setReassignTarget(null)}
          onReassigned={() => { setReassignTarget(null); triggerRefresh(); }}
          recordId={reassignTarget.record_id}
          releasedGuardName={reassignTarget.guard.name}
          postId={reassignTarget.post_id}
          postName={reassignTarget.post || 'Unknown Post'}
          shiftTemplateId={reassignTarget.shift_template_id}
          shiftName={reassignTarget.shift || 'Unknown Shift'}
        />
      )}

      {incidentTarget && (
        <IncidentModal
          visible={!!incidentTarget}
          onClose={() => setIncidentTarget(null)}
          onLogged={() => setIncidentTarget(null)}
          employeeId={incidentTarget.guard.id}
          guardName={incidentTarget.guard.name}
        />
      )}

      {profileTarget && (
        <GuardProfileModal
          visible={!!profileTarget}
          onClose={() => setProfileTarget(null)}
          guardId={profileTarget.id}
          guardName={profileTarget.name}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  loader: { flex: 1, backgroundColor: Theme.colors.background, justifyContent: 'center', alignItems: 'center' },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 12,
    gap: 10,
  },
  backBtn: {
    padding: 4,
    borderRadius: 8,
  },
  pdfBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: `${Theme.colors.primary}12`,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerInfo: { flex: 1 },
  siteName: { fontSize: 16, fontWeight: '700', color: Theme.colors.text },
  clientName: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 1 },
  stateChip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: `${Theme.colors.scheduled}14`,
    borderColor: Theme.colors.scheduled,
    borderWidth: 1,
  },
  capturedChip: {
    backgroundColor: `${Theme.colors.primary}14`,
    borderColor: Theme.colors.primary,
  },
  stateChipText: { fontSize: 10, fontWeight: '700', color: Theme.colors.text },
  cachedChip: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: `${Theme.colors.accentGold}14`,
    borderColor: Theme.colors.accentGold,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  search: {
    margin: 12,
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    elevation: 0,
  },
  syncChip: {
    backgroundColor: Theme.colors.primary,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    paddingHorizontal: 16,
    marginHorizontal: 12,
    marginBottom: 8,
    borderRadius: 8,
  },
  syncChipText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  bulkMarkChip: {
    backgroundColor: Theme.colors.present,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    paddingHorizontal: 16,
    marginHorizontal: 12,
    marginBottom: 8,
    borderRadius: 8,
  },
  list: { paddingHorizontal: 12, paddingBottom: 100 },
  noShiftBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: `${Theme.colors.scheduled}10`,
    borderColor: Theme.colors.scheduled,
    borderWidth: 1,
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  noShiftText: { fontSize: 12, color: Theme.colors.scheduled, flex: 1, fontWeight: '600' },
  errBox: { alignItems: 'center', marginTop: 64, gap: 12 },
  errText: { color: Theme.colors.absent, textAlign: 'center' },
  errBtn: { marginTop: 8, borderColor: Theme.colors.absent },
  empty: { alignItems: 'center', marginTop: 64, gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14 },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: Theme.colors.primary,
  },
  fabAdd: {
    bottom: 0,
    right: 0,
    backgroundColor: Theme.colors.secondary,
  },
  fabAddShifted: {
    bottom: 72,
  },
});
