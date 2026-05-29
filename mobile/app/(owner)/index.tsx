import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { Text, ActivityIndicator, Card } from 'react-native-paper';
import { getOwnerKpis, OwnerKpisResponse } from '../../src/api/owner';
import { Theme } from '../../src/theme';
import KpiMetric from '../../src/components/KpiMetric';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function OwnerDashboardScreen() {
  const [data, setData] = useState<OwnerKpisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const loadKpis = async (silent = false) => {
    if (!silent) setLoading(true);
    setErrorMsg('');
    try {
      const res = await getOwnerKpis();
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch executive KPIs.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadKpis();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadKpis(true);
  };

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={Theme.colors.primary} />
      </View>
    );
  }

  return (
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
      ) : null}

      {!errorMsg && data ? (
        <View style={styles.kpiGrid}>
          <View style={styles.row}>
            <KpiMetric
              title="Attendance Rate"
              value={`${data.attendance.rate_percent}%`}
              icon="account-check-outline"
              color={Theme.colors.present}
              subtitle="Target: 95%"
            />
            <KpiMetric
              title="Active Guards"
              value={data.total_guards}
              icon="shield-account-outline"
              color={Theme.colors.primary}
              subtitle="On payroll active list"
            />
          </View>

          <View style={styles.row}>
            <KpiMetric
              title="Open Incidents"
              value={data.open_incidents}
              icon="alert-octagon-outline"
              color={Theme.colors.absent}
              subtitle="Immediate action required"
            />
            <KpiMetric
              title="Active Sites"
              value={data.sites_active}
              icon="office-building-marker-outline"
              color={Theme.colors.accentCyan}
              subtitle="Revenue generating posts"
            />
          </View>

          {/* Financial KPI Banner */}
          <Card style={styles.financialCard}>
            <Card.Content>
              <Text style={styles.financialHeader}>FINANCIAL SUMMARY</Text>
              <View style={styles.financialRow}>
                <View style={styles.financialBlock}>
                  <Text style={styles.finLabel}>Payroll Cost YTD</Text>
                  <Text style={styles.finVal}>N${data.payroll_cost_ytd.toLocaleString()}</Text>
                </View>
                <View style={styles.dividerVertical} />
                <View style={styles.financialBlock}>
                  <Text style={styles.finLabel}>Outstanding Invoices</Text>
                  <Text style={[styles.finVal, { color: Theme.colors.accentGold }]}>
                    N${data.outstanding_invoices.toLocaleString()}
                  </Text>
                </View>
              </View>
            </Card.Content>
          </Card>

          {/* Top Sites Roster List */}
          <Text style={styles.sectionTitle}>Top Sites By Attendance</Text>
          {data.top_sites_by_attendance && data.top_sites_by_attendance.map((site) => (
            <Card key={site.site_id} style={styles.topSiteCard}>
              <Card.Content style={styles.topSiteContent}>
                <View style={styles.topSiteInfo}>
                  <Text style={styles.topSiteName}>{site.site_name}</Text>
                  <Text style={styles.topSiteClient}>{site.client}</Text>
                </View>
                <View style={styles.topSiteRateBox}>
                  <Text style={styles.topSiteRate}>{site.attendance_rate}%</Text>
                  <Text style={styles.topSiteLabel}>ATTENDANCE</Text>
                </View>
              </Card.Content>
            </Card>
          ))}
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0B0F',
  },
  scroll: {
    padding: 16,
    paddingBottom: 40,
  },
  loader: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    justifyContent: 'center',
    alignItems: 'center',
  },
  kpiGrid: {
    gap: 16,
  },
  row: {
    flexDirection: 'row',
    gap: 16,
  },
  financialCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 20,
    marginTop: 8,
  },
  financialHeader: {
    fontSize: 10,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    letterSpacing: 1,
    marginBottom: 16,
  },
  financialRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  financialBlock: {
    flex: 1,
  },
  finLabel: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    marginBottom: 4,
  },
  finVal: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
    letterSpacing: -0.5,
  },
  dividerVertical: {
    width: 1,
    height: 40,
    backgroundColor: Theme.colors.border,
    marginHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 16,
    marginBottom: 8,
  },
  topSiteCard: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 10,
  },
  topSiteContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  topSiteInfo: {
    flex: 1,
  },
  topSiteName: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#FFF',
  },
  topSiteClient: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    marginTop: 2,
  },
  topSiteRateBox: {
    alignItems: 'flex-end',
  },
  topSiteRate: {
    fontSize: 16,
    fontWeight: 'bold',
    color: Theme.colors.present,
  },
  topSiteLabel: {
    fontSize: 8,
    color: Theme.colors.placeholder,
    fontWeight: 'bold',
    marginTop: 2,
  },
  errorBox: {
    alignItems: 'center',
    marginTop: 64,
    gap: 12,
  },
  errorText: {
    color: Theme.colors.absent,
    textAlign: 'center',
  },
});
