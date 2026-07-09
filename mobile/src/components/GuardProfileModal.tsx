import React, { useEffect, useState } from 'react';
import { View, StyleSheet, TouchableOpacity, Linking } from 'react-native';
import { Text, Modal, Portal, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { getGuardProfile, GuardProfileData } from '../api/supervisor';
import { Theme } from '../theme';

interface Props {
  visible: boolean;
  onClose: () => void;
  guardId: number;
  guardName: string;
}

const PRESENCE_COLOR: Record<string, string> = {
  present: Theme.colors.present,
  absent: Theme.colors.absent,
  awol: '#F97316',
  not_marked: Theme.colors.accentGold,
  no_shift: Theme.colors.border,
};

const PRESENCE_ICON: Record<string, string> = {
  present: 'check-circle',
  absent: 'close-circle',
  awol: 'alert-circle',
  not_marked: 'clock-outline',
  no_shift: 'minus-circle-outline',
};

function ReliabilityRing({ score }: { score: number | null }) {
  const pct = score ?? 0;
  const color = pct >= 85 ? Theme.colors.present : pct >= 65 ? Theme.colors.accentGold : Theme.colors.absent;
  return (
    <View style={[styles.reliabilityRing, { borderColor: color }]}>
      <Text style={[styles.reliabilityScore, { color }]}>{score !== null ? score : '—'}</Text>
      <Text style={[styles.reliabilityLabel, { color }]}>SCORE</Text>
    </View>
  );
}

function AttendanceDot({ day }: { day: { date: string; presence: string } }) {
  const color = PRESENCE_COLOR[day.presence] || Theme.colors.border;
  const dayLabel = new Date(day.date).toLocaleDateString('en', { weekday: 'narrow' });
  return (
    <View style={styles.dotCol}>
      <MaterialCommunityIcons
        name={PRESENCE_ICON[day.presence] as any}
        size={18}
        color={color}
      />
      <Text style={styles.dotDay}>{dayLabel}</Text>
    </View>
  );
}

export default function GuardProfileModal({ visible, onClose, guardId, guardName }: Props) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<GuardProfileData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!visible) return;
    setLoading(true);
    setData(null);
    setError('');
    getGuardProfile(guardId)
      .then(setData)
      .catch((err) => setError(err.message || 'Failed to load profile'))
      .finally(() => setLoading(false));
  }, [visible, guardId]);

  const handleCall = () => {
    if (data?.mobile_phone) Linking.openURL(`tel:${data.mobile_phone}`);
  };

  return (
    <Portal>
      <Modal visible={visible} onDismiss={onClose} contentContainerStyle={styles.modal}>
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <MaterialCommunityIcons name="shield-account" size={18} color={Theme.colors.primary} />
            <Text style={styles.headerName} numberOfLines={1}>{guardName}</Text>
          </View>
          <TouchableOpacity onPress={onClose} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <MaterialCommunityIcons name="close" size={22} color={Theme.colors.placeholder} />
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={styles.loader}>
            <ActivityIndicator size="large" color={Theme.colors.primary} />
          </View>
        ) : error || !data ? (
          <View style={styles.loader}>
            <Text style={styles.errorText}>{error || 'No data found.'}</Text>
          </View>
        ) : (
          <View style={styles.body}>
            {/* Score + meta row */}
            <View style={styles.topRow}>
              <ReliabilityRing score={data.reliability_score} />
              <View style={styles.metaCol}>
                {data.grade && (
                  <View style={styles.gradeBadge}>
                    <Text style={styles.gradeText}>{data.grade}</Text>
                  </View>
                )}
                {data.site && (
                  <View style={styles.metaRow}>
                    <MaterialCommunityIcons name="map-marker-outline" size={13} color={Theme.colors.placeholder} />
                    <Text style={styles.metaText} numberOfLines={1}>{data.site}</Text>
                  </View>
                )}
                {data.mobile_phone && (
                  <TouchableOpacity style={styles.callBtn} onPress={handleCall} activeOpacity={0.75}>
                    <MaterialCommunityIcons name="phone-outline" size={13} color={Theme.colors.primary} />
                    <Text style={styles.callText}>{data.mobile_phone}</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>

            {/* Active leave alert */}
            {data.active_leave && (
              <View style={styles.leaveBanner}>
                <MaterialCommunityIcons name="beach" size={14} color={Theme.colors.accentCyan} />
                <Text style={styles.leaveText}>
                  On {data.active_leave.leave_type} leave · {data.active_leave.date_from} → {data.active_leave.date_to}
                </Text>
              </View>
            )}

            {/* Open incidents */}
            {data.open_incidents > 0 && (
              <View style={styles.incidentBanner}>
                <MaterialCommunityIcons name="shield-alert-outline" size={14} color="#DC2626" />
                <Text style={styles.incidentText}>
                  {data.open_incidents} open incident{data.open_incidents !== 1 ? 's' : ''} pending review
                </Text>
              </View>
            )}

            {/* 7-day attendance */}
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>LAST 7 DAYS</Text>
              <View style={styles.dotsRow}>
                {data.attendance_7d.map((d) => (
                  <AttendanceDot key={d.date} day={d} />
                ))}
              </View>
              <View style={styles.legendRow}>
                {[
                  { label: 'Present', color: Theme.colors.present },
                  { label: 'Absent', color: Theme.colors.absent },
                  { label: 'AWOL', color: '#F97316' },
                  { label: 'No shift', color: Theme.colors.border },
                ].map((l) => (
                  <View key={l.label} style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: l.color }]} />
                    <Text style={styles.legendText}>{l.label}</Text>
                  </View>
                ))}
              </View>
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
    margin: 20,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: Theme.colors.border,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 },
  headerName: { fontSize: 16, fontWeight: 'bold', color: Theme.colors.text, flex: 1 },
  loader: { height: 140, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: Theme.colors.absent, fontSize: 13 },
  body: { padding: 16, gap: 12 },
  topRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 16 },
  reliabilityRing: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
  },
  reliabilityScore: { fontSize: 22, fontWeight: 'bold' },
  reliabilityLabel: { fontSize: 8, fontWeight: '800', letterSpacing: 0.5, marginTop: -2 },
  metaCol: { flex: 1, gap: 6, justifyContent: 'center' },
  gradeBadge: {
    alignSelf: 'flex-start',
    backgroundColor: `${Theme.colors.accentGold}14`,
    borderColor: Theme.colors.accentGold,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  gradeText: { color: Theme.colors.accentGold, fontSize: 11, fontWeight: 'bold' },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  metaText: { fontSize: 12, color: Theme.colors.onSurface, flex: 1 },
  callBtn: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  callText: { fontSize: 12, color: Theme.colors.primary, fontWeight: '600' },
  leaveBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: `${Theme.colors.accentCyan}14`,
    borderColor: `${Theme.colors.accentCyan}40`,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  leaveText: { fontSize: 12, color: Theme.colors.accentCyan, fontWeight: '600', flex: 1 },
  incidentBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FEF2F2',
    borderColor: '#FECACA',
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  incidentText: { fontSize: 12, color: '#DC2626', fontWeight: '600', flex: 1 },
  section: { gap: 8 },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: Theme.colors.placeholder,
    letterSpacing: 0.8,
  },
  dotsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 12,
    padding: 12,
  },
  dotCol: { alignItems: 'center', gap: 4 },
  dotDay: { fontSize: 9, color: Theme.colors.placeholder, fontWeight: '600' },
  legendRow: { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 7, height: 7, borderRadius: 3.5 },
  legendText: { fontSize: 10, color: Theme.colors.placeholder },
});
