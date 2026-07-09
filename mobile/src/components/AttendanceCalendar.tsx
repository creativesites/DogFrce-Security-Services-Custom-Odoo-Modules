import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ScrollView,
} from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { CalendarDay } from '../api/owner';
import { Theme } from '../theme';

interface Props {
  days: CalendarDay[];
  periodStart: string;
}

function cellColor(d: CalendarDay): string {
  if (!d.has_data) return Theme.colors.border;
  if (d.rate >= 90) return Theme.colors.present;
  if (d.rate >= 70) return Theme.colors.accentGold;
  return Theme.colors.absent;
}

function cellOpacity(d: CalendarDay): number {
  if (!d.has_data) return 0.25;
  if (d.rate >= 90) return 1;
  if (d.rate >= 70) return 0.85;
  return 0.9;
}

const DOW_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function AttendanceCalendar({ days, periodStart }: Props) {
  const [selected, setSelected] = useState<CalendarDay | null>(null);

  // Build grid: days array already covers the full month; pad start with empties
  const firstDate = new Date(periodStart + 'T00:00:00');
  // 0=Sun→6, we want Mon=0 offset
  const firstDow = (firstDate.getDay() + 6) % 7;
  const grid: (CalendarDay | null)[] = [
    ...Array(firstDow).fill(null),
    ...days,
  ];
  // Pad end to fill last row
  while (grid.length % 7 !== 0) grid.push(null);

  const weeks: (CalendarDay | null)[][] = [];
  for (let i = 0; i < grid.length; i += 7) weeks.push(grid.slice(i, i + 7));

  return (
    <View>
      {/* Day-of-week header */}
      <View style={styles.dowRow}>
        {DOW_LABELS.map((lbl) => (
          <Text key={lbl} style={styles.dowLabel}>{lbl}</Text>
        ))}
      </View>

      {/* Weeks */}
      {weeks.map((week, wi) => (
        <View key={wi} style={styles.weekRow}>
          {week.map((day, di) => {
            if (!day) return <View key={di} style={styles.emptyCell} />;
            const dayNum = new Date(day.date + 'T00:00:00').getDate();
            return (
              <TouchableOpacity
                key={di}
                style={[
                  styles.cell,
                  {
                    backgroundColor: cellColor(day),
                    opacity: cellOpacity(day),
                  },
                ]}
                onPress={() => setSelected(day)}
                activeOpacity={0.7}
              >
                <Text style={styles.cellDay}>{dayNum}</Text>
                {day.has_data && (
                  <Text style={styles.cellRate}>{day.rate}%</Text>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
      ))}

      {/* Legend */}
      <View style={styles.legend}>
        {[
          { color: Theme.colors.present, label: '≥90%' },
          { color: Theme.colors.accentGold, label: '70–89%' },
          { color: Theme.colors.absent, label: '<70%' },
          { color: Theme.colors.border, label: 'No data' },
        ].map(({ color, label }) => (
          <View key={label} style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: color }]} />
            <Text style={styles.legendLabel}>{label}</Text>
          </View>
        ))}
      </View>

      {/* Day detail modal */}
      <Modal
        visible={!!selected}
        transparent
        animationType="fade"
        onRequestClose={() => setSelected(null)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setSelected(null)}
        >
          {selected && (
            <View style={styles.modalCard}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalDate}>
                  {new Date(selected.date + 'T00:00:00').toLocaleDateString('en-GB', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </Text>
                <TouchableOpacity onPress={() => setSelected(null)}>
                  <MaterialCommunityIcons name="close" size={20} color={Theme.colors.placeholder} />
                </TouchableOpacity>
              </View>
              {selected.has_data ? (
                <>
                  <View style={styles.modalRate}>
                    <Text style={[styles.modalRateNum, { color: cellColor(selected) }]}>
                      {selected.rate}%
                    </Text>
                    <Text style={styles.modalRateLabel}>attendance rate</Text>
                  </View>
                  <View style={styles.modalStats}>
                    {[
                      { label: 'Sites', value: selected.sites, color: Theme.colors.primary },
                      { label: 'Total', value: selected.total, color: Theme.colors.text },
                      { label: 'Present', value: selected.present, color: Theme.colors.present },
                      { label: 'Absent', value: selected.absent, color: Theme.colors.absent },
                      { label: 'AWOL', value: selected.awol, color: Theme.colors.accentGold },
                    ].map(({ label, value, color }) => (
                      <View key={label} style={styles.modalStat}>
                        <Text style={[styles.modalStatNum, { color }]}>{value}</Text>
                        <Text style={styles.modalStatLabel}>{label}</Text>
                      </View>
                    ))}
                  </View>
                </>
              ) : (
                <View style={styles.noDataBox}>
                  <MaterialCommunityIcons name="calendar-blank-outline" size={32} color={Theme.colors.placeholder} />
                  <Text style={styles.noDataText}>No attendance records for this day</Text>
                </View>
              )}
            </View>
          )}
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const CELL_SIZE = 44;

const styles = StyleSheet.create({
  dowRow: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  dowLabel: {
    width: CELL_SIZE,
    textAlign: 'center',
    fontSize: 10,
    fontWeight: '600',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginHorizontal: 1,
  },
  weekRow: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  cell: {
    width: CELL_SIZE,
    height: CELL_SIZE,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 1,
  },
  emptyCell: {
    width: CELL_SIZE,
    height: CELL_SIZE,
    marginHorizontal: 1,
  },
  cellDay: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFF',
    lineHeight: 14,
  },
  cellRate: {
    fontSize: 8,
    color: 'rgba(255,255,255,0.85)',
    lineHeight: 11,
  },
  legend: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 16,
    marginTop: 12,
    flexWrap: 'wrap',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendLabel: {
    fontSize: 10,
    color: Theme.colors.placeholder,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalCard: {
    backgroundColor: Theme.colors.surface,
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxWidth: 360,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  modalDate: {
    fontSize: 14,
    fontWeight: '600',
    color: Theme.colors.text,
    flex: 1,
    marginRight: 8,
  },
  modalRate: {
    alignItems: 'center',
    marginBottom: 20,
  },
  modalRateNum: {
    fontSize: 48,
    fontWeight: 'bold',
    letterSpacing: -2,
  },
  modalRateLabel: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  modalStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  modalStat: {
    alignItems: 'center',
  },
  modalStatNum: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  modalStatLabel: {
    fontSize: 10,
    color: Theme.colors.placeholder,
    marginTop: 2,
  },
  noDataBox: {
    alignItems: 'center',
    gap: 12,
    paddingVertical: 16,
  },
  noDataText: {
    color: Theme.colors.placeholder,
    fontSize: 13,
    textAlign: 'center',
  },
});
