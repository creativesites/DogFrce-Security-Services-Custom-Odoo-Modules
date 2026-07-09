import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text, Avatar } from 'react-native-paper';
import { Theme } from '../theme';
import StatusBadge from './StatusBadge';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface GuardCardProps {
  name: string;
  grade: string | null;
  post: string | null;
  shift: string | null;
  status: string;
  checkIn: string | null;
  checkOut: string | null;
  onPress?: () => void;
  onReassign?: () => void;
  onIncident?: () => void;
  onProfile?: () => void;
}

export const GuardCard: React.FC<GuardCardProps> = ({
  name, grade, post, shift, status, checkIn, checkOut, onPress, onReassign, onIncident, onProfile,
}) => {
  const getInitials = (n: string) =>
    n.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase();

  const formatTime = (iso: string | null) => {
    if (!iso) return '--:--';
    try {
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return '--:--'; }
  };

  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={onPress}
      disabled={!onPress}
      style={[styles.card, onPress && styles.tappable]}
    >
      <View style={styles.header}>
        <View style={styles.left}>
          <Avatar.Text
            size={40}
            label={getInitials(name)}
            style={styles.avatar}
            labelStyle={styles.avatarLabel}
          />
          <View style={styles.guardMeta}>
            <Text style={styles.name}>{name}</Text>
            {grade && (
              <View style={styles.gradeContainer}>
                <Text style={styles.gradeText}>{grade}</Text>
              </View>
            )}
          </View>
        </View>
        <StatusBadge status={status} />
      </View>

      <View style={styles.divider} />

      <View style={styles.body}>
        <View style={styles.infoRow}>
          <MaterialCommunityIcons name="shield-outline" size={15} color={Theme.colors.placeholder} />
          <Text style={styles.infoText}>{post || 'Unassigned Post'}</Text>
        </View>
        <View style={styles.infoRow}>
          <MaterialCommunityIcons name="clock-outline" size={15} color={Theme.colors.placeholder} />
          <Text style={styles.infoText}>{shift || 'Unscheduled Shift'}</Text>
        </View>
      </View>

      {(checkIn || checkOut) && (
        <View style={styles.footer}>
          <View style={styles.timeBlock}>
            <Text style={styles.timeLabel}>CHECK IN</Text>
            <Text style={styles.timeVal}>{formatTime(checkIn)}</Text>
          </View>
          <View style={styles.timeDivider} />
          <View style={styles.timeBlock}>
            <Text style={styles.timeLabel}>CHECK OUT</Text>
            <Text style={styles.timeVal}>{formatTime(checkOut)}</Text>
          </View>
        </View>
      )}

      {onPress && (
        <MaterialCommunityIcons
          name="chevron-right"
          size={18}
          color={Theme.colors.placeholder}
          style={styles.chevron}
        />
      )}

      {(onReassign || onIncident || onProfile) && (
        <View style={styles.actionRow}>
          {onProfile && (
            <TouchableOpacity style={[styles.actionBtn, styles.profileBtn]} onPress={onProfile} activeOpacity={0.75}>
              <MaterialCommunityIcons name="account-details-outline" size={13} color="#fff" />
              <Text style={styles.actionBtnLabel}>Profile</Text>
            </TouchableOpacity>
          )}
          {onReassign && (
            <TouchableOpacity style={[styles.actionBtn, styles.reassignBtn]} onPress={onReassign} activeOpacity={0.75}>
              <MaterialCommunityIcons name="account-switch-outline" size={13} color="#fff" />
              <Text style={styles.actionBtnLabel}>Reassign</Text>
            </TouchableOpacity>
          )}
          {onIncident && (
            <TouchableOpacity style={[styles.actionBtn, styles.incidentBtn]} onPress={onIncident} activeOpacity={0.75}>
              <MaterialCommunityIcons name="shield-alert-outline" size={13} color="#fff" />
              <Text style={styles.actionBtnLabel}>Log Incident</Text>
            </TouchableOpacity>
          )}
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
    padding: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  tappable: {
    borderLeftWidth: 3,
    borderLeftColor: Theme.colors.primary,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  left: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  avatar: { backgroundColor: `${Theme.colors.primary}14` },
  avatarLabel: { color: Theme.colors.primary, fontWeight: 'bold', fontSize: 14 },
  guardMeta: { marginLeft: 10, flex: 1 },
  name: { fontSize: 15, fontWeight: '700', color: Theme.colors.text },
  gradeContainer: {
    backgroundColor: `${Theme.colors.accentGold}14`,
    borderColor: Theme.colors.accentGold,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
    marginTop: 3,
    alignSelf: 'flex-start',
  },
  gradeText: { color: Theme.colors.accentGold, fontSize: 10, fontWeight: 'bold' },
  divider: { height: 1, backgroundColor: Theme.colors.border, marginVertical: 10 },
  body: { gap: 6 },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  infoText: { color: Theme.colors.onSurface, fontSize: 13 },
  footer: {
    flexDirection: 'row',
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 8,
    padding: 10,
    marginTop: 10,
  },
  timeBlock: { alignItems: 'center', flex: 1 },
  timeDivider: { width: 1, backgroundColor: Theme.colors.border, marginHorizontal: 8 },
  timeLabel: { fontSize: 9, color: Theme.colors.placeholder, fontWeight: 'bold', marginBottom: 2 },
  timeVal: { fontSize: 13, color: Theme.colors.text, fontWeight: 'bold' },
  chevron: { position: 'absolute', top: 14, right: 14 },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 10,
  },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    borderRadius: 8,
    paddingVertical: 8,
  },
  profileBtn: { backgroundColor: Theme.colors.primary },
  reassignBtn: { backgroundColor: '#DC2626' },
  incidentBtn: { backgroundColor: '#7C3AED' },
  actionBtnLabel: { color: '#fff', fontSize: 12, fontWeight: '700' },
});

export default GuardCard;
