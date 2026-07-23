import React, { useEffect, useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Linking,
} from 'react-native';
import { Text, ActivityIndicator, Button, Card } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../../src/theme';
import { getGuardToday, guardCheckIn, guardSendSOS, GuardTodayData } from '../../src/api/guard';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';

export default function GuardHomeScreen() {
  const [data, setData] = useState<GuardTodayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checkingIn, setCheckingIn] = useState(false);
  const [sendingSOS, setSendingSOS] = useState(false);

  const loadData = async () => {
    try {
      const res = await getGuardToday();
      setData(res);
    } catch (err: any) {
      console.warn('Failed to load guard today info:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelfCheckIn = async (action: 'check_in' | 'check_out') => {
    setCheckingIn(true);
    try {
      // 1. Get GPS Location
      let locCoords: { latitude: number; longitude: number; accuracy?: number } | undefined;
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const currentLoc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        locCoords = {
          latitude: currentLoc.coords.latitude,
          longitude: currentLoc.coords.longitude,
          accuracy: currentLoc.coords.accuracy ?? undefined,
        };
      }

      // 2. Prompt for optional camera selfie verification
      let photoB64: string | undefined;
      const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
      if (cameraStatus === 'granted') {
        const pickerRes = await ImagePicker.launchCameraAsync({
          quality: 0.5,
          base64: true,
          allowsEditing: false,
        });
        if (!pickerRes.canceled && pickerRes.assets && pickerRes.assets[0]?.base64) {
          photoB64 = pickerRes.assets[0].base64;
        }
      }

      // 3. Send check-in request
      await guardCheckIn(action, locCoords, photoB64);
      Alert.alert(
        'Success',
        action === 'check_in' ? 'Successfully checked in to your post.' : 'Successfully checked out.'
      );
      loadData();
    } catch (err: any) {
      Alert.alert('Check-In Error', err.message || 'Failed to record check-in.');
    } finally {
      setCheckingIn(false);
    }
  };

  const handleSOSAlert = () => {
    Alert.alert(
      '🚨 EMERGENCY PANIC ALERT',
      'Are you sure you want to trigger an immediate Emergency SOS Alert to your supervisor and operations center?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'TRIGGER SOS NOW',
          style: 'destructive',
          onPress: async () => {
            setSendingSOS(true);
            try {
              let locCoords: { latitude: number; longitude: number } | undefined;
              const { status } = await Location.requestForegroundPermissionsAsync();
              if (status === 'granted') {
                const currentLoc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
                locCoords = {
                  latitude: currentLoc.coords.latitude,
                  longitude: currentLoc.coords.longitude,
                };
              }
              const res = await guardSendSOS(locCoords, 'GUARD PANIC BUTTON TRIGGERED');
              Alert.alert('🚨 EMERGENCY ALERT SENT', res.message || 'Alert dispatched to supervisor.');
            } catch (err: any) {
              Alert.alert('SOS Error', err.message || 'Failed to dispatch SOS alert.');
            } finally {
              setSendingSOS(false);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  const isCheckedIn = data?.attendance?.status === 'present' && !!data.attendance.check_in && !data.attendance.check_out;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => { setRefreshing(true); loadData(); }}
          colors={[Theme.colors.primary]}
          tintColor={Theme.colors.primary}
        />
      }
    >
      {/* Guard Profile Banner */}
      <View style={styles.profileCard}>
        <View style={styles.avatarCircle}>
          <MaterialCommunityIcons name="account-circle" size={48} color={Theme.colors.primary} />
        </View>
        <View style={styles.profileMeta}>
          <Text style={styles.guardName}>{data?.guard.name || 'Guard Profile'}</Text>
          <View style={styles.badgeRow}>
            <View style={styles.gradeBadge}>
              <Text style={styles.gradeText}>{data?.guard.grade || 'Grade C'}</Text>
            </View>
            <Text style={styles.reliabilityText}>
              Reliability Score: <Text style={{ fontWeight: '700', color: Theme.colors.present }}>{data?.guard.reliability_score ?? 95}%</Text>
            </Text>
          </View>
        </View>
      </View>

      {/* Emergency SOS Button */}
      <TouchableOpacity
        style={styles.sosButton}
        onPress={handleSOSAlert}
        disabled={sendingSOS}
        activeOpacity={0.8}
      >
        <MaterialCommunityIcons name="alert-decagram" size={28} color="#FFF" />
        <View style={styles.sosTextWrapper}>
          <Text style={styles.sosTitle}>EMERGENCY SOS PANIC</Text>
          <Text style={styles.sosSubtitle}>Tap to dispatch instant emergency alert</Text>
        </View>
      </TouchableOpacity>

      {/* Today's Shift Assignment */}
      <Text style={styles.sectionTitle}>Today's Shift Assignment</Text>

      {data?.has_assignment ? (
        <Card style={styles.shiftCard}>
          <Card.Content style={styles.shiftContent}>
            <View style={styles.siteHeader}>
              <View style={styles.siteIconWrapper}>
                <MaterialCommunityIcons name="office-building-marker" size={24} color={Theme.colors.primary} />
              </View>
              <View style={styles.siteTitleBox}>
                <Text style={styles.siteName}>{data.site?.name || 'Assigned Site'}</Text>
                <Text style={styles.postName}>{data.post ? `Post: ${data.post}` : 'General Duty'}</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.shiftRow}>
              <View style={styles.infoCol}>
                <Text style={styles.label}>Shift Template</Text>
                <Text style={styles.val}>{data.shift?.name || 'Day Shift'}</Text>
              </View>
              <View style={styles.infoCol}>
                <Text style={styles.label}>Hours</Text>
                <Text style={styles.val}>
                  {data.shift ? `${data.shift.start_hour}:00 - ${data.shift.end_hour}:00` : '06:00 - 18:00'}
                </Text>
              </View>
            </View>

            {data.supervisor && (
              <View style={styles.supBox}>
                <MaterialCommunityIcons name="account-tie" size={20} color={Theme.colors.placeholder} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.supLabel}>Supervisor on Duty</Text>
                  <Text style={styles.supName}>{data.supervisor.name}</Text>
                </View>
                {data.supervisor.phone && (
                  <TouchableOpacity
                    style={styles.callBtn}
                    onPress={() => Linking.openURL(`tel:${data.supervisor?.phone}`)}
                  >
                    <MaterialCommunityIcons name="phone" size={18} color="#FFF" />
                  </TouchableOpacity>
                )}
              </View>
            )}
          </Card.Content>
        </Card>
      ) : (
        <View style={styles.noShiftCard}>
          <MaterialCommunityIcons name="calendar-blank-outline" size={40} color={Theme.colors.placeholder} />
          <Text style={styles.noShiftText}>No shift assigned for today.</Text>
        </View>
      )}

      {/* Self Check-In / Out Action */}
      {data?.has_assignment && (
        <View style={styles.actionSection}>
          <Text style={styles.sectionTitle}>Check-In Status</Text>

          <View style={styles.statusBox}>
            <MaterialCommunityIcons
              name={isCheckedIn ? 'check-circle' : 'clock-outline'}
              size={24}
              color={isCheckedIn ? Theme.colors.present : Theme.colors.scheduled}
            />
            <View style={{ flex: 1 }}>
              <Text style={styles.statusTitle}>
                {isCheckedIn ? 'Currently Checked In' : 'Not Checked In Yet'}
              </Text>
              {data?.attendance?.check_in && (
                <Text style={styles.statusTime}>Check-In Time: {data.attendance.check_in}</Text>
              )}
            </View>
          </View>

          {!isCheckedIn ? (
            <Button
              mode="contained"
              icon="camera-account"
              onPress={() => handleSelfCheckIn('check_in')}
              loading={checkingIn}
              disabled={checkingIn}
              style={styles.checkInBtn}
              labelStyle={styles.btnLabel}
            >
              SELF CHECK-IN WITH GPS
            </Button>
          ) : (
            <Button
              mode="outlined"
              icon="logout-variant"
              onPress={() => handleSelfCheckIn('check_out')}
              loading={checkingIn}
              disabled={checkingIn}
              style={styles.checkOutBtn}
              labelStyle={{ color: Theme.colors.absent, fontWeight: '700' }}
            >
              CHECK-OUT OF POST
            </Button>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  content: { padding: 16, paddingBottom: 40 },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Theme.colors.background },
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    marginBottom: 16,
    gap: 12,
  },
  avatarCircle: { width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center' },
  profileMeta: { flex: 1 },
  guardName: { fontSize: 18, fontWeight: '700', color: Theme.colors.text },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  gradeBadge: {
    backgroundColor: `${Theme.colors.primary}15`,
    borderColor: Theme.colors.primary,
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  gradeText: { fontSize: 10, fontWeight: '700', color: Theme.colors.primary },
  reliabilityText: { fontSize: 12, color: Theme.colors.placeholder },
  sosButton: {
    backgroundColor: '#DC2626',
    borderRadius: 14,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
    elevation: 4,
  },
  sosTextWrapper: { flex: 1 },
  sosTitle: { color: '#FFF', fontSize: 15, fontWeight: '800', letterSpacing: 0.5 },
  sosSubtitle: { color: '#FEE2E2', fontSize: 11, marginTop: 2 },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: Theme.colors.text, marginBottom: 10 },
  shiftCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 20,
    elevation: 0,
  },
  shiftContent: { padding: 16 },
  siteHeader: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  siteIconWrapper: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: `${Theme.colors.primary}12`,
    alignItems: 'center',
    justifyContent: 'center',
  },
  siteTitleBox: { flex: 1 },
  siteName: { fontSize: 16, fontWeight: '700', color: Theme.colors.text },
  postName: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  divider: { height: 1, backgroundColor: Theme.colors.border, marginVertical: 12 },
  shiftRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  infoCol: { flex: 1 },
  label: { fontSize: 11, color: Theme.colors.placeholder },
  val: { fontSize: 13, fontWeight: '700', color: Theme.colors.text, marginTop: 2 },
  supBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: `${Theme.colors.primary}08`,
    padding: 10,
    borderRadius: 10,
    marginTop: 4,
  },
  supLabel: { fontSize: 10, color: Theme.colors.placeholder },
  supName: { fontSize: 13, fontWeight: '700', color: Theme.colors.text },
  callBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Theme.colors.present,
    justifyContent: 'center',
    alignItems: 'center',
  },
  noShiftCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 20,
  },
  noShiftText: { fontSize: 14, color: Theme.colors.placeholder },
  actionSection: { gap: 10 },
  statusBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    gap: 12,
    marginBottom: 8,
  },
  statusTitle: { fontSize: 14, fontWeight: '700', color: Theme.colors.text },
  statusTime: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  checkInBtn: {
    backgroundColor: Theme.colors.present,
    borderRadius: 12,
    paddingVertical: 6,
  },
  checkOutBtn: {
    borderColor: Theme.colors.absent,
    borderRadius: 12,
    paddingVertical: 6,
  },
  btnLabel: { fontSize: 14, fontWeight: '800', color: '#FFF' },
});
