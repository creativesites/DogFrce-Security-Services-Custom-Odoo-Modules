import React, { useState, useEffect, useMemo } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TextInput, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator, Card, SegmentedButtons } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { getOwnerGuards, OwnerGuard } from '../../src/api/owner';
import { Theme } from '../../src/theme';

type Period = '7' | '30' | '90';

function rateColor(rate: number): string {
  if (rate >= 90) return Theme.colors.present;
  if (rate >= 70) return Theme.colors.accentGold;
  return Theme.colors.absent;
}

function rateIcon(rate: number): string {
  if (rate >= 90) return 'shield-check-outline';
  if (rate >= 70) return 'shield-alert-outline';
  return 'shield-off-outline';
}

export default function OwnerGuardsScreen() {
  const [guards, setGuards] = useState<OwnerGuard[]>([]);
  const [meta, setMeta] = useState({ period_days: 30, period_start: '' });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [period, setPeriod] = useState<Period>('30');
  const [search, setSearch] = useState('');
  const router = useRouter();

  const load = async (days: number, silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getOwnerGuards(days);
      setGuards(res.guards);
      setMeta({ period_days: res.period_days, period_start: res.period_start });
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load guards.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(Number(period)); }, [period]);

  const onRefresh = () => { setRefreshing(true); load(Number(period), true); };

  const filtered = useMemo(() => {
    if (!search.trim()) return guards;
    const q = search.toLowerCase();
    return guards.filter((g) => g.name.toLowerCase().includes(q) || (g.grade ?? '').toLowerCase().includes(q));
  }, [guards, search]);

  const renderGuard = ({ item, index }: { item: OwnerGuard; index: number }) => {
    const onPress = () => router.push(`/(owner)/guard/${item.id}`);
    const color = rateColor(item.stats.rate);
    const icon = rateIcon(item.stats.rate);
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.75}>
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.cardHeader}>
            <View style={[styles.rankBadge, { borderColor: color }]}>
              <Text style={[styles.rankNum, { color }]}>{index + 1}</Text>
            </View>
            <View style={styles.nameBlock}>
              <Text style={styles.guardName}>{item.name}</Text>
              <View style={styles.subRow}>
                {item.grade && (
                  <View style={styles.gradePill}>
                    <Text style={styles.gradeText}>{item.grade}</Text>
                  </View>
                )}
                {item.last_shift && (
                  <Text style={styles.lastShift}>
                    Last shift: {new Date(item.last_shift + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                  </Text>
                )}
              </View>
            </View>
            <View style={styles.rateBlock}>
              <MaterialCommunityIcons name={icon as any} size={18} color={color} />
              <Text style={[styles.rateNum, { color }]}>
                {item.stats.total > 0 ? `${item.stats.rate}%` : '—'}
              </Text>
            </View>
          </View>

          {item.stats.total > 0 && (
            <View style={styles.statsRow}>
              <MiniStat value={item.stats.total} label="Total" color={Theme.colors.text} />
              <MiniStat value={item.stats.present} label="Present" color={Theme.colors.present} />
              <MiniStat value={item.stats.absent} label="Absent" color={Theme.colors.absent} />
              <MiniStat value={item.stats.awol} label="AWOL" color={Theme.colors.accentGold} />
              {item.stats.late > 0 && (
                <MiniStat value={item.stats.late} label="Late" color={Theme.colors.late} />
              )}
            </View>
          )}

          {/* Reliability score if available */}
          {item.reliability_score !== null && item.reliability_score !== undefined && (
            <View style={styles.reliabilityRow}>
              <Text style={styles.reliabilityLabel}>Reliability Score</Text>
              <View style={styles.reliabilityBar}>
                <View style={[styles.reliabilityFill, {
                  width: `${Math.min(100, item.reliability_score)}%`,
                  backgroundColor: rateColor(item.reliability_score),
                }]} />
              </View>
              <Text style={[styles.reliabilityScore, { color: rateColor(item.reliability_score) }]}>
                {item.reliability_score}%
              </Text>
            </View>
          )}
        </Card.Content>
      </Card>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.wrapper}>
      {/* Period selector */}
      <View style={styles.controls}>
        <SegmentedButtons
          value={period}
          onValueChange={(v) => setPeriod(v as Period)}
          buttons={[
            { value: '7', label: '7 days' },
            { value: '30', label: '30 days' },
            { value: '90', label: '90 days' },
          ]}
          style={styles.segmented}
          density="small"
        />
        <View style={styles.searchBox}>
          <MaterialCommunityIcons name="magnify" size={18} color={Theme.colors.placeholder} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search guards…"
            placeholderTextColor={Theme.colors.placeholder}
            value={search}
            onChangeText={setSearch}
            autoCorrect={false}
          />
          {search.length > 0 && (
            <MaterialCommunityIcons
              name="close-circle"
              size={16}
              color={Theme.colors.placeholder}
              onPress={() => setSearch('')}
            />
          )}
        </View>
      </View>

      {loading ? (
        <View style={styles.loader}>
          <ActivityIndicator size="large" color={Theme.colors.primary} />
        </View>
      ) : errorMsg ? (
        <View style={styles.errorBox}>
          <MaterialCommunityIcons name="alert-circle-outline" size={32} color={Theme.colors.absent} />
          <Text style={styles.errorText}>{errorMsg}</Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(g) => String(g.id)}
          renderItem={renderGuard}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Theme.colors.primary]} />}
          ListHeaderComponent={
            <Text style={styles.hint}>
              {filtered.length} guard{filtered.length !== 1 ? 's' : ''} · last {meta.period_days} days · worst → best
            </Text>
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <MaterialCommunityIcons name="shield-off-outline" size={40} color={Theme.colors.placeholder} />
              <Text style={styles.emptyText}>{search ? 'No guards match your search.' : 'No guard records found.'}</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

function MiniStat({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <View style={styles.miniStat}>
      <Text style={[styles.miniStatNum, { color }]}>{value}</Text>
      <Text style={styles.miniStatLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: Theme.colors.background },
  controls: { padding: 16, paddingBottom: 8, gap: 10 },
  segmented: { borderRadius: 12 },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Theme.colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    color: Theme.colors.text,
    padding: 0,
  },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorBox: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, padding: 32 },
  errorText: { color: Theme.colors.absent, textAlign: 'center' },
  list: { paddingHorizontal: 16, paddingBottom: 40 },
  hint: { fontSize: 11, color: Theme.colors.placeholder, marginBottom: 12 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 10,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12, gap: 12 },
  rankBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },
  rankNum: { fontSize: 13, fontWeight: 'bold' },
  nameBlock: { flex: 1 },
  guardName: { fontSize: 14, fontWeight: 'bold', color: Theme.colors.text },
  subRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4, flexWrap: 'wrap' },
  gradePill: {
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  gradeText: { fontSize: 9, fontWeight: '600', color: Theme.colors.placeholder, textTransform: 'uppercase' },
  lastShift: { fontSize: 10, color: Theme.colors.placeholder },
  rateBlock: { alignItems: 'center', gap: 2 },
  rateNum: { fontSize: 15, fontWeight: 'bold' },
  statsRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 8 },
  miniStat: {
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    alignItems: 'center',
    minWidth: 44,
  },
  miniStatNum: { fontSize: 13, fontWeight: 'bold' },
  miniStatLabel: { fontSize: 8, color: Theme.colors.placeholder, textTransform: 'uppercase', marginTop: 1 },
  reliabilityRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  reliabilityLabel: { fontSize: 10, color: Theme.colors.placeholder, width: 100 },
  reliabilityBar: {
    flex: 1,
    height: 6,
    backgroundColor: Theme.colors.surfaceVariant,
    borderRadius: 3,
    overflow: 'hidden',
  },
  reliabilityFill: { height: 6, borderRadius: 3 },
  reliabilityScore: { fontSize: 11, fontWeight: 'bold', width: 36, textAlign: 'right' },
  empty: { marginTop: 80, alignItems: 'center', gap: 12 },
  emptyText: { color: Theme.colors.placeholder, fontSize: 14, textAlign: 'center' },
});
