import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { Text, ActivityIndicator, Card } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { getOwnerCalendar, CalendarResponse } from '../../src/api/owner';
import AttendanceCalendar from '../../src/components/AttendanceCalendar';
import PeriodNavigator from '../../src/components/PeriodNavigator';
import { Theme } from '../../src/theme';

function currentMonth(): string {
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  return `${now.getFullYear()}-${mm}`;
}

export default function OwnerCalendarScreen() {
  const [data, setData] = useState<CalendarResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(currentMonth);

  const load = async (month: string, silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getOwnerCalendar(month);
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load calendar data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(selectedMonth); }, [selectedMonth]);

  const onRefresh = () => { setRefreshing(true); load(selectedMonth, true); };

  // Compute summary stats for the month
  const totalDays = data?.days.filter((d) => d.has_data).length ?? 0;
  const avgRate = totalDays > 0
    ? Math.round(data!.days.filter((d) => d.has_data).reduce((s, d) => s + d.rate, 0) / totalDays)
    : 0;
  const bestDay = data?.days.reduce<typeof data.days[0] | null>((best, d) => {
    if (!d.has_data) return best;
    return !best || d.rate > best.rate ? d : best;
  }, null);
  const worstDay = data?.days.reduce<typeof data.days[0] | null>((worst, d) => {
    if (!d.has_data) return worst;
    return !worst || d.rate < worst.rate ? d : worst;
  }, null);

  return (
    <View style={styles.wrapper}>
      <PeriodNavigator mode="month" value={selectedMonth} onChange={setSelectedMonth} />

      {loading ? (
        <View style={styles.loader}>
          <ActivityIndicator size="large" color={Theme.colors.primary} />
        </View>
      ) : (
        <ScrollView
          style={styles.container}
          contentContainerStyle={styles.scroll}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
        >
          {errorMsg ? (
            <View style={styles.errorBox}>
              <MaterialCommunityIcons name="alert-circle-outline" size={32} color={Theme.colors.absent} />
              <Text style={styles.errorText}>{errorMsg}</Text>
            </View>
          ) : data ? (
            <>
              {/* Month summary cards */}
              <View style={styles.summaryRow}>
                <Card style={[styles.summaryCard, { flex: 1 }]}>
                  <Card.Content style={styles.summaryContent}>
                    <Text style={styles.summaryNum}>{avgRate}%</Text>
                    <Text style={styles.summaryLabel}>Avg Rate</Text>
                  </Card.Content>
                </Card>
                <Card style={[styles.summaryCard, { flex: 1 }]}>
                  <Card.Content style={styles.summaryContent}>
                    <Text style={[styles.summaryNum, { color: Theme.colors.present }]}>
                      {bestDay ? `${bestDay.rate}%` : '—'}
                    </Text>
                    <Text style={styles.summaryLabel}>Best Day</Text>
                    {bestDay && (
                      <Text style={styles.summaryDate}>
                        {new Date(bestDay.date + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                      </Text>
                    )}
                  </Card.Content>
                </Card>
                <Card style={[styles.summaryCard, { flex: 1 }]}>
                  <Card.Content style={styles.summaryContent}>
                    <Text style={[styles.summaryNum, { color: Theme.colors.absent }]}>
                      {worstDay ? `${worstDay.rate}%` : '—'}
                    </Text>
                    <Text style={styles.summaryLabel}>Worst Day</Text>
                    {worstDay && (
                      <Text style={styles.summaryDate}>
                        {new Date(worstDay.date + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                      </Text>
                    )}
                  </Card.Content>
                </Card>
              </View>

              {/* Calendar heatmap */}
              <Card style={styles.calCard}>
                <Card.Content>
                  <Text style={styles.calTitle}>{data.month}</Text>
                  <Text style={styles.calHint}>Tap a day for details</Text>
                  <AttendanceCalendar days={data.days} periodStart={data.period_start} />
                </Card.Content>
              </Card>

              {/* Day-by-day list for days with issues */}
              {data.days.filter((d) => d.has_data && d.rate < 80).length > 0 && (
                <>
                  <Text style={styles.sectionTitle}>Days Below 80%</Text>
                  {data.days
                    .filter((d) => d.has_data && d.rate < 80)
                    .sort((a, b) => a.rate - b.rate)
                    .map((d) => (
                      <Card key={d.date} style={styles.flagCard}>
                        <Card.Content style={styles.flagContent}>
                          <View style={styles.flagLeft}>
                            <Text style={styles.flagDate}>
                              {new Date(d.date + 'T00:00:00').toLocaleDateString('en-GB', {
                                weekday: 'short', day: 'numeric', month: 'short',
                              })}
                            </Text>
                            <Text style={styles.flagSites}>{d.sites} site{d.sites !== 1 ? 's' : ''} · {d.total} guards</Text>
                          </View>
                          <View style={styles.flagStats}>
                            <Text style={[styles.flagRate, {
                              color: d.rate >= 70 ? Theme.colors.accentGold : Theme.colors.absent
                            }]}>{d.rate}%</Text>
                            <View style={styles.flagBreakdown}>
                              <Text style={[styles.flagChip, { color: Theme.colors.absent }]}>{d.absent} absent</Text>
                              <Text style={[styles.flagChip, { color: Theme.colors.accentGold }]}>{d.awol} AWOL</Text>
                            </View>
                          </View>
                        </Card.Content>
                      </Card>
                    ))}
                </>
              )}
            </>
          ) : null}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: Theme.colors.background },
  container: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorBox: { alignItems: 'center', marginTop: 64, gap: 12 },
  errorText: { color: Theme.colors.absent, textAlign: 'center' },
  summaryRow: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  summaryCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
  },
  summaryContent: { alignItems: 'center', paddingHorizontal: 4, paddingVertical: 12 },
  summaryNum: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Theme.colors.text,
    letterSpacing: -0.5,
  },
  summaryLabel: { fontSize: 10, color: Theme.colors.placeholder, textTransform: 'uppercase', marginTop: 2 },
  summaryDate: { fontSize: 10, color: Theme.colors.placeholder, marginTop: 2 },
  calCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 20,
    marginBottom: 16,
  },
  calTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: Theme.colors.text,
    marginBottom: 2,
  },
  calHint: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
  },
  flagCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 14,
    marginBottom: 8,
  },
  flagContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  flagLeft: { flex: 1 },
  flagDate: { fontSize: 13, fontWeight: '600', color: Theme.colors.text },
  flagSites: { fontSize: 11, color: Theme.colors.placeholder, marginTop: 2 },
  flagStats: { alignItems: 'flex-end' },
  flagRate: { fontSize: 18, fontWeight: 'bold' },
  flagBreakdown: { flexDirection: 'row', gap: 8, marginTop: 2 },
  flagChip: { fontSize: 10, fontWeight: '600' },
});
