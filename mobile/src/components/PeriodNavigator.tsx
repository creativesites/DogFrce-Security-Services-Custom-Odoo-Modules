import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../theme';

interface Props {
  mode: 'day' | 'month';
  value: string; // YYYY-MM-DD (day) or YYYY-MM (month)
  onChange: (value: string) => void;
}

function formatLabel(mode: 'day' | 'month', value: string): string {
  try {
    if (mode === 'day') {
      const d = new Date(value + 'T00:00:00');
      return d.toLocaleDateString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
    } else {
      const [y, m] = value.split('-').map(Number);
      const d = new Date(y, m - 1, 1);
      return d.toLocaleDateString('en-ZA', { month: 'long', year: 'numeric' });
    }
  } catch {
    return value;
  }
}

function shift(mode: 'day' | 'month', value: string, dir: -1 | 1): string {
  if (mode === 'day') {
    const d = new Date(value + 'T00:00:00');
    d.setDate(d.getDate() + dir);
    return d.toISOString().split('T')[0];
  } else {
    const [y, m] = value.split('-').map(Number);
    const next = new Date(y, m - 1 + dir, 1);
    const mm = String(next.getMonth() + 1).padStart(2, '0');
    return `${next.getFullYear()}-${mm}`;
  }
}

function todayValue(mode: 'day' | 'month'): string {
  const now = new Date();
  if (mode === 'day') return now.toISOString().split('T')[0];
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  return `${now.getFullYear()}-${mm}`;
}

export default function PeriodNavigator({ mode, value, onChange }: Props) {
  const today = todayValue(mode);
  const isToday = value === today;
  const isFuture = value > today;

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.arrow}
        onPress={() => onChange(shift(mode, value, -1))}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <MaterialCommunityIcons name="chevron-left" size={22} color={Theme.colors.text} />
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.labelWrap}
        onPress={() => onChange(today)}
        disabled={isToday}
        activeOpacity={0.7}
      >
        <Text style={styles.label}>{formatLabel(mode, value)}</Text>
        {!isToday && (
          <View style={styles.todayChip}>
            <Text style={styles.todayChipText}>{mode === 'day' ? 'Go to today' : 'Current month'}</Text>
          </View>
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.arrow, isFuture && styles.arrowDisabled]}
        onPress={() => !isFuture && onChange(shift(mode, value, 1))}
        disabled={isFuture}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <MaterialCommunityIcons
          name="chevron-right"
          size={22}
          color={isFuture ? Theme.colors.border : Theme.colors.text}
        />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  arrow: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: Theme.colors.surfaceVariant,
  },
  arrowDisabled: { opacity: 0.3 },
  labelWrap: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
  },
  label: {
    fontSize: 15,
    fontWeight: '700',
    color: Theme.colors.text,
  },
  todayChip: {
    backgroundColor: `${Theme.colors.primary}12`,
    borderColor: Theme.colors.primary,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  todayChipText: {
    fontSize: 10,
    color: Theme.colors.primary,
    fontWeight: '600',
  },
});
