import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import { Theme } from '../theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface SiteKpiCardProps {
  siteName: string;
  client: string;
  supervisor: string | null;
  totalSlots: number;
  present: number;
  absent: number;
  awol: number;
  late: number;
  attendanceRate: number;
  batchState: string;
  onPress: () => void;
}

export const SiteKpiCard: React.FC<SiteKpiCardProps> = ({
  siteName, client, supervisor, totalSlots, present, absent, awol, late,
  attendanceRate, batchState, onPress,
}) => {
  const getProgressColor = () => {
    if (attendanceRate >= 90) return Theme.colors.present;
    if (attendanceRate >= 70) return Theme.colors.awol;
    return Theme.colors.absent;
  };

  const getBatchStateBadge = () => {
    switch (batchState) {
      case 'captured':  return { label: 'CAPTURED', color: Theme.colors.primary };
      case 'confirmed': return { label: 'CONFIRMED', color: Theme.colors.present };
      case 'cancelled': return { label: 'CANCELLED', color: Theme.colors.absent };
      case 'draft':     return { label: 'IN PROGRESS', color: Theme.colors.scheduled };
      default:          return { label: 'NO SHIFT YET', color: Theme.colors.placeholder };
    }
  };

  const stateBadge = getBatchStateBadge();
  const progressColor = getProgressColor();

  return (
    <TouchableOpacity activeOpacity={0.8} onPress={onPress} style={styles.card}>
      <View style={styles.header}>
        <View style={styles.titleSec}>
          <Text style={styles.siteName}>{siteName}</Text>
          <Text style={styles.clientName}>{client}</Text>
        </View>
        <View style={[styles.batchBadge, { backgroundColor: `${stateBadge.color}14`, borderColor: stateBadge.color }]}>
          <Text style={[styles.batchBadgeText, { color: stateBadge.color }]}>{stateBadge.label}</Text>
        </View>
      </View>

      <View style={styles.rateRow}>
        <Text style={styles.rateLabel}>Attendance Rate</Text>
        <Text style={[styles.rateVal, { color: progressColor }]}>{attendanceRate}%</Text>
      </View>

      <View style={styles.progressBarBg}>
        <View
          style={[styles.progressBarFg, { width: `${Math.min(attendanceRate, 100)}%`, backgroundColor: progressColor }]}
        />
      </View>

      <View style={styles.statsGrid}>
        <View style={styles.statBox}>
          <Text style={[styles.statNum, { color: Theme.colors.present }]}>{present}</Text>
          <Text style={styles.statLabel}>Present</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={[styles.statNum, { color: Theme.colors.late }]}>{late}</Text>
          <Text style={styles.statLabel}>Late</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={[styles.statNum, { color: Theme.colors.absent }]}>{absent}</Text>
          <Text style={styles.statLabel}>Absent</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={[styles.statNum, { color: Theme.colors.awol }]}>{awol}</Text>
          <Text style={styles.statLabel}>AWOL</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statNum}>{totalSlots}</Text>
          <Text style={styles.statLabel}>Total</Text>
        </View>
      </View>

      {supervisor && (
        <View style={styles.footer}>
          <MaterialCommunityIcons name="account-tie" size={13} color={Theme.colors.placeholder} />
          <Text style={styles.supervisorName}>{supervisor}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  titleSec: { flex: 1, marginRight: 8 },
  siteName: { fontSize: 17, fontWeight: 'bold', color: Theme.colors.text },
  clientName: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  batchBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, borderWidth: 1 },
  batchBadgeText: { fontSize: 9, fontWeight: 'bold' },
  rateRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 14 },
  rateLabel: { color: Theme.colors.onSurface, fontSize: 13 },
  rateVal: { fontSize: 16, fontWeight: 'bold' },
  progressBarBg: {
    height: 5,
    backgroundColor: Theme.colors.border,
    borderRadius: 3,
    marginTop: 6,
    overflow: 'hidden',
  },
  progressBarFg: { height: '100%', borderRadius: 3 },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 14,
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 10,
    padding: 10,
  },
  statBox: { alignItems: 'center', flex: 1 },
  statNum: { fontSize: 14, fontWeight: 'bold', color: Theme.colors.text },
  statLabel: { fontSize: 10, color: Theme.colors.placeholder, marginTop: 2, fontWeight: '600' },
  footer: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 5 },
  supervisorName: { fontSize: 11, color: Theme.colors.placeholder },
});

export default SiteKpiCard;
