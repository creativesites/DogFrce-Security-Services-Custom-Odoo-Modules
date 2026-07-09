import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../theme';

interface StatusBadgeProps {
  status: 'present' | 'absent' | 'awol' | 'scheduled' | 'late' | 'not_marked' | 'queued' | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  let label = status.toUpperCase().replace('_', ' ');
  let color = Theme.colors.not_marked;
  let bg = 'rgba(107, 114, 128, 0.15)';
  let icon: string | null = null;

  switch (status) {
    case 'present':
      color = Theme.colors.present;
      bg = 'rgba(16, 185, 129, 0.15)';
      break;
    case 'absent':
      color = Theme.colors.absent;
      bg = 'rgba(239, 68, 68, 0.15)';
      break;
    case 'awol':
      color = Theme.colors.awol;
      bg = 'rgba(245, 158, 11, 0.15)';
      break;
    case 'late':
      color = Theme.colors.late;
      bg = 'rgba(244, 63, 94, 0.15)';
      break;
    case 'scheduled':
    case 'assigned':
    case 'confirmed':
      color = Theme.colors.scheduled;
      bg = 'rgba(59, 130, 246, 0.15)';
      label = 'SCHEDULED';
      break;
    case 'queued':
      color = '#D97706';
      bg = 'rgba(217, 119, 6, 0.15)';
      label = 'QUEUED';
      icon = 'cloud-upload-outline';
      break;
  }

  return (
    <View style={[styles.badge, { backgroundColor: bg, borderColor: color }]}>
      {icon && <MaterialCommunityIcons name={icon as any} size={10} color={color} style={styles.icon} />}
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    alignSelf: 'flex-start',
    gap: 4,
  },
  icon: { marginRight: 1 },
  text: {
    fontSize: 11,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
});
export default StatusBadge;
