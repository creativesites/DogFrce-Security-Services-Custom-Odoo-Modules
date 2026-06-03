import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Button, TextInput, RadioButton, ActivityIndicator, Avatar } from 'react-native-paper';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getTodayPostingSheet, markPresence, quickCheckIn, AttendanceRecord } from '../../../src/api/supervisor';
import { useAppStore } from '../../../src/stores/appStore';
import { enqueuePresenceMark } from '../../../src/utils/offlineQueue';
import { isOffline } from '../../../src/api/client';
import { Theme } from '../../../src/theme';
import CheckInButton from '../../../src/components/CheckInButton';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function MarkGuardScreen() {
  const { recordId } = useLocalSearchParams();
  const [record, setRecord] = useState<AttendanceRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Custom states matching editable fields
  const [presence, setPresence] = useState<'present' | 'absent' | 'awol' | 'not_marked'>('not_marked');
  const [note, setNote] = useState('');
  
  const { triggerRefresh } = useAppStore();
  const router = useRouter();

  const loadRecord = async () => {
    setLoading(true);
    try {
      const today = await getTodayPostingSheet();
      const matched = today.slots?.find((s) => s.record_id === Number(recordId));
      if (matched) {
        setRecord(matched);
        setPresence(matched.manual_presence);
        setNote(matched.override_reason || '');
      }
    } catch (err) {
      console.error('Failed to load guard record detail', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecord();
  }, [recordId]);

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
        // Queue for later sync
        await enqueuePresenceMark({
          recordId: Number(recordId),
          presence,
          overrideReason: note || undefined,
        });
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
        <Text style={styles.errorText}>Guard record not found.</Text>
        <Button mode="contained" onPress={() => router.back()} style={styles.backBtn}>
          Go Back
        </Button>
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
      </View>

      {/* Immediate Check-In / Check-Out */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Check In / Check Out</Text>
        <View style={styles.checkInRow}>
          {!record.check_in ? (
            <CheckInButton action="check_in" onPress={() => handleCheckInOut('check_in')} />
          ) : !record.check_out ? (
            <View style={styles.timeFilledRow}>
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>CHECKED IN</Text>
                <Text style={styles.timeVal}>
                  {new Date(record.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
              <CheckInButton action="check_out" onPress={() => handleCheckInOut('check_out')} />
            </View>
          ) : (
            <View style={styles.completedTimes}>
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>CHECKED IN</Text>
                <Text style={styles.timeVal}>
                  {new Date(record.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>CHECKED OUT</Text>
                <Text style={styles.timeVal}>
                  {new Date(record.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
            </View>
          )}
        </View>
      </View>

      {/* Manual Override Status Toggles */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Manual Attendance Marking</Text>
        <RadioButton.Group onValueChange={(val) => setPresence(val as any)} value={presence}>
          <View style={styles.radioOption}>
            <RadioButton value="present" color={Theme.colors.present} />
            <Text style={[styles.radioLabel, presence === 'present' && { color: Theme.colors.present }]}>Present</Text>
          </View>
          <View style={styles.radioOption}>
            <RadioButton value="absent" color={Theme.colors.absent} />
            <Text style={[styles.radioLabel, presence === 'absent' && { color: Theme.colors.absent }]}>Absent</Text>
          </View>
          <View style={styles.radioOption}>
            <RadioButton value="awol" color={Theme.colors.awol} />
            <Text style={[styles.radioLabel, presence === 'awol' && { color: Theme.colors.awol }]}>AWOL</Text>
          </View>
          <View style={styles.radioOption}>
            <RadioButton value="not_marked" color={Theme.colors.placeholder} />
            <Text style={styles.radioLabel}>Not Marked</Text>
          </View>
        </RadioButton.Group>
      </View>

      {/* Override / Exception notes */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Exception Notes</Text>
        <TextInput
          value={note}
          onChangeText={setNote}
          placeholder="e.g. Guard late due to transport delay, client authorised overtime..."
          mode="outlined"
          multiline
          numberOfLines={4}
          style={styles.textArea}
          outlineColor={Theme.colors.border}
          activeOutlineColor={Theme.colors.primary}
          textColor={Theme.colors.text}
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
        Save Roster Record
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#0B0B0F',
    padding: 20,
  },
  loader: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardHeader: {
    alignItems: 'center',
    marginVertical: 20,
    backgroundColor: Theme.colors.surface,
    padding: 24,
    borderRadius: 24,
    borderColor: Theme.colors.border,
    borderWidth: 1,
  },
  avatar: {
    backgroundColor: Theme.colors.surfaceVariant,
    marginBottom: 12,
  },
  avatarLabel: {
    color: Theme.colors.primary,
    fontWeight: 'bold',
  },
  guardName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
    textAlign: 'center',
  },
  gradeBadge: {
    backgroundColor: 'rgba(251, 191, 36, 0.1)',
    borderColor: Theme.colors.accentGold,
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginTop: 8,
  },
  gradeText: {
    color: Theme.colors.accentGold,
    fontSize: 11,
    fontWeight: 'bold',
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
  checkInRow: {
    width: '100%',
  },
  timeFilledRow: {
    width: '100%',
    gap: 16,
  },
  timeBox: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    flex: 1,
  },
  timeLabel: {
    fontSize: 10,
    color: Theme.colors.placeholder,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  timeVal: {
    fontSize: 18,
    color: '#FFF',
    fontWeight: 'bold',
  },
  completedTimes: {
    flexDirection: 'row',
    gap: 12,
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  radioLabel: {
    color: Theme.colors.onSurface,
    fontSize: 15,
    marginLeft: 8,
  },
  textArea: {
    backgroundColor: 'transparent',
  },
  saveBtn: {
    paddingVertical: 8,
    borderRadius: 12,
    marginTop: 12,
    marginBottom: 40,
  },
  saveBtnLabel: {
    fontWeight: 'bold',
    fontSize: 16,
  },
  errorText: {
    color: Theme.colors.absent,
    marginBottom: 16,
  },
  backBtn: {
    borderRadius: 12,
  },
});
