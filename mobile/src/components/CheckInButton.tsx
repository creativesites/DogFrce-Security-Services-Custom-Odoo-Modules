import React from 'react';
import { StyleSheet, TouchableOpacity, View } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { Theme } from '../theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface CheckInButtonProps {
  action: 'check_in' | 'check_out';
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
}

export const CheckInButton: React.FC<CheckInButtonProps> = ({
  action,
  onPress,
  loading = false,
  disabled = false,
}) => {
  const isCheckIn = action === 'check_in';
  const color = isCheckIn ? Theme.colors.present : Theme.colors.absent;
  const bg = isCheckIn ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)';
  const icon = isCheckIn ? 'login' : 'logout';
  const text = isCheckIn ? 'TAP TO CHECK IN GUARD' : 'TAP TO CHECK OUT GUARD';

  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={onPress}
      disabled={disabled || loading}
      style={[
        styles.button,
        {
          backgroundColor: bg,
          borderColor: color,
        },
        disabled && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={color} />
      ) : (
        <View style={styles.content}>
          <MaterialCommunityIcons name={icon} size={24} color={color} />
          <Text style={[styles.text, { color }]}>{text}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    height: 72,
    borderRadius: 16,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
    width: '100%',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  text: {
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  disabled: {
    opacity: 0.5,
  },
});
export default CheckInButton;
