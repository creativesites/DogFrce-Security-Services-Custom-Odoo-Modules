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
}

export const GuardCard: React.FC<GuardCardProps> = ({
  name,
  grade,
  post,
  shift,
  status,
  checkIn,
  checkOut,
  onPress,
}) => {
  const getInitials = (n: string) => {
    return n.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase();
  };

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '--:--';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '--:--';
    }
  };

  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={onPress}
      disabled={!onPress}
      style={styles.card}
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
          <MaterialCommunityIcons name="shield-outline" size={16} color={Theme.colors.placeholder} />
          <Text style={styles.infoText}>{post || 'Unassigned Post'}</Text>
        </View>
        <View style={styles.infoRow}>
          <MaterialCommunityIcons name="clock-outline" size={16} color={Theme.colors.placeholder} />
          <Text style={styles.infoText}>{shift || 'Unscheduled Shift'}</Text>
        </View>
      </View>

      {(checkIn || checkOut) && (
        <View style={styles.footer}>
          <View style={styles.timeBlock}>
            <Text style={styles.timeLabel}>CHECK IN</Text>
            <Text style={styles.timeVal}>{formatTime(checkIn)}</Text>
          </View>
          <View style={styles.timeBlock}>
            <Text style={styles.timeLabel}>CHECK OUT</Text>
            <Text style={styles.timeVal}>{formatTime(checkOut)}</Text>
          </View>
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
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  left: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  avatar: {
    backgroundColor: Theme.colors.surfaceVariant,
  },
  avatarLabel: {
    color: Theme.colors.primary,
    fontWeight: 'bold',
    fontSize: 14,
  },
  guardMeta: {
    marginLeft: 12,
    flex: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: 'bold',
    color: Theme.colors.text,
  },
  gradeContainer: {
    backgroundColor: 'rgba(251, 191, 36, 0.1)',
    borderColor: Theme.colors.accentGold,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 1,
    marginTop: 4,
    alignSelf: 'flex-start',
  },
  gradeText: {
    color: Theme.colors.accentGold,
    fontSize: 10,
    fontWeight: 'bold',
  },
  divider: {
    height: 1,
    backgroundColor: Theme.colors.border,
    marginVertical: 12,
  },
  body: {
    gap: 8,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  infoText: {
    color: Theme.colors.onSurface,
    fontSize: 13,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    padding: 10,
    marginTop: 12,
    borderColor: Theme.colors.border,
    borderWidth: 1,
  },
  timeBlock: {
    alignItems: 'center',
    flex: 1,
  },
  timeLabel: {
    fontSize: 9,
    color: Theme.colors.placeholder,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  timeVal: {
    fontSize: 13,
    color: Theme.colors.text,
    fontWeight: 'bold',
  },
});
export default GuardCard;
