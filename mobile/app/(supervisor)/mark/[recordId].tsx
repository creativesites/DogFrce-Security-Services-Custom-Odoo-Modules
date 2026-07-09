import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Button, TextInput, RadioButton, ActivityIndicator, Avatar } from 'react-native-paper';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getSitePostingSheet, markPresence, quickCheckIn, AttendanceRecord } from '../../../src/api/supervisor';
import { useAppStore } from '../../../src/stores/appStore';
import { enqueuePresenceMark } from '../../../src/utils/offlineQueue';
import { isOffline } from '../../../src/api/client';
import { Theme } from '../../../src/theme';
import CheckInButton from '../../../src/components/CheckInButton';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function MarkGuardScreen() {
  const { recordId, siteId } = useLocalSearchParams<{ recordId: string; siteId: string }>();
  const [record, setRecord] = useState<AttendanceRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [presence, setPresence] = useState<'present' | 'absent' | 'awol' | 'not_marked'>('not_marked');
  const [note, setNote] = useState('');

  const { triggerRefresh } = useAppStore();
  const router = useRouter();

  const loadRecord = async () => {
    setLoading(true);
    try {
      const sheet = await getSitePostingSheet(Number(siteId));
      const matched = sheet.slots?.find((s) => s.record_id === Number(recordId));
      if (matched) {
        setRecord(matched);
        setPresence(matched.manual_presence);
        setNote(matched.override_reason || '');
      }
    } catch (err) {
      console.error('Failed to load guard record', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRecord(); }, [recordId, siteId]);

  const handleCheckInOut = async (action: 'check_in' | 'check_out') => {
    try {
      const updated = await quickCheckIn(Number(recordId), action);
      setRecord(updated);
      setPresence(updated.manual_presence);
      triggerRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to register timestamp.');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await markPresence(Number(recordId), presence, note);
      triggerRefresh();
      router.back();
    } catch (err: any) {
      if (isOffline) {
        await enqueuePresenceMark({ recordId: Number(recordId), presence, overrideReason: note || undefined });
        alert('Offline: mark queued for sync when connection is restored.');
        router.back();
      } else {
        alert(err.message || 'Failed to update attendance.');
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  if (!record) {
    return (
      <View style={styles.loader}>
        <MaterialCommunityIcons name="account-alert-outline" size={48} color={Theme.colors.placeholder} />
        <Text style={styles.errorText}>Guard record not found.</Text>
        <Button mode="contained" onPress={() => router.back()} style={styles.backBtn}>Go Back</Button>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.cardHeader}>
        <Avatar.Text
          size={64}
          label={record.guard.name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()}
          style={styles.avatar}
          labelStyle={styles.avatarLabel}
        />
        <Text style={styles.guardName}>{record.guard.name}</Text>
        {record.guard.grade && (
          <View style={styles.gradeBadge}>
            <Text style={styles.gradeText}>{record.guard.grade}</Text>
          </View>
        )}
        <View style={styles.postInfo}>
          {record.post && (
            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="shield-outline" size={14} color={Theme.colors.placeholder} />
              <Text style={styles.metaText}>{record.post}</Text>
            </View>
          )}
          {record.shift && (
            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="clock-outline" size={14} color={Theme.colors.placeholder} />
              <Text style={styles.metaText}>{record.shift}</Text>
            </View>
          )}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Check In / Check Out</Text>
        <View style={styles.checkInRow}>
          {!record.check_in ? (
            <CheckInButton action="check_in" onPress={() => handleCheckInOut('check_in')} />
          ) : !record.check_out ? (
            <View style={styles.timeRow}>
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>CHECKED IN</Text>
                <Text style={styles.timeVal}>
                  {new Date(record.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
              <CheckInButton action="check_out" onPress={() => handleCheckInOut('check_out')} />
            </View>
          ) : (
            <View style={styles.timesComplete}>
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>CHECKED IN</Text>
                <Text style={styles.timeVal}>
                  {new Date(record.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>CHECKED OUT</Text>
                <Text style={styles.timeVal}>
                  {new Date(record.check_out!).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
            </View>
          )}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Attendance Status</Text>
        <View style={styles.radioCard}>
          <RadioButton.Group onValueChange={(val) => setPresence(val as any)} value={presence}>
            {[
              { val: 'present', label: 'Present', color: Theme.colors.present },
              { val: 'absent', label: 'Absent', color: Theme.colors.absent },
              { val: 'awol', label: 'AWOL', color: Theme.colors.awol },
              { val: 'not_marked', label: 'Not Marked', color: Theme.colors.placeholder },
            ].map(opt => (
              <View key={opt.val} style={styles.radioOption}>
                <RadioButton value={opt.val} color={opt.color} />
                <Text style={[styles.radioLabel, presence === opt.val && { color: opt.color, fontWeight: '700' }]}>
                  {opt.label}
                </Text>
              </View>
            ))}
          </RadioButton.Group>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Exception Notes</Text>
        <TextInput
          value={note}
          onChangeText={setNote}
          placeholder="e.g. Guard late due to transport delay..."
          mode="outlined"
          multiline
          numberOfLines={3}
          style={styles.textArea}
          outlineColor={Theme.colors.border}
          activeOutlineColor={Theme.colors.primary}
        />
      </View>

      <Button
        mode="contained"
        onPress={handleSave}
        loading={saving}
        disabled={saving}
        style={styles.saveBtn}
        labelStyle={styles.saveBtnLabel}
      >
        Save Record
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: Theme.colors.background, padding: 16, paddingBottom: 40 },
  loader: { flex: 1, backgroundColor: Theme.colors.background, justifyContent: 'center', alignItems: 'center', gap: 16 },
  cardHeader: {
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    padding: 24,
    borderRadius: 20,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  avatar: { backgroundColor: `${Theme.colors.primary}18`, marginBottom: 10 },
  avatarLabel: { color: Theme.colors.primary, fontWeight: 'bold' },
  guardName: { fontSize: 20, fontWeight: 'bold', color: Theme.colors.text, textAlign: 'center' },
  gradeBadge: {
    backgroundColor: `${Theme.colors.accentGold}14`,
    borderColor: Theme.colors.accentGold,
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginTop: 6,
  },
  gradeText: { color: Theme.colors.accentGold, fontSize: 11, fontWeight: 'bold' },
  postInfo: { marginTop: 10, gap: 4, alignItems: 'center' },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  metaText: { fontSize: 12, color: Theme.colors.placeholder },
  section: { marginBottom: 20 },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 10,
  },
  checkInRow: { width: '100%' },
  timeRow: { gap: 12 },
  timesComplete: { flexDirection: 'row', gap: 12 },
  timeBox: {
    flex: 1,
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
  },
  timeLabel: { fontSize: 10, color: Theme.colors.placeholder, fontWeight: 'bold', marginBottom: 4 },
  timeVal: { fontSize: 18, color: Theme.colors.text, fontWeight: 'bold' },
  radioCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 8,
  },
  radioOption: { flexDirection: 'row', alignItems: 'center', paddingVertical: 4 },
  radioLabel: { color: Theme.colors.onSurface, fontSize: 15, marginLeft: 4 },
  textArea: { backgroundColor: Theme.colors.surface },
  saveBtn: { paddingVertical: 6, borderRadius: 12, marginTop: 8 },
  saveBtnLabel: { fontWeight: 'bold', fontSize: 16 },
  errorText: { color: Theme.colors.placeholder, fontSize: 15 },
  backBtn: { borderRadius: 12 },
});
