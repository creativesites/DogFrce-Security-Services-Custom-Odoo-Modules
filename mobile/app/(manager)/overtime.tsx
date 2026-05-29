import React, { useState } from 'react';
import { View, StyleSheet, FlatList } from 'react-native';
import { Text, Card, Button } from 'react-native-paper';
import { Theme } from '../../src/theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface MockOtRequest {
  id: string;
  guardName: string;
  siteName: string;
  post: string;
  hours: number;
  reason: string;
}

export default function GlobalOvertimeScreen() {
  const [requests, setRequests] = useState<MockOtRequest[]>([
    { id: '1', guardName: 'Silas Kamati', siteName: 'Acme HQ', post: 'Main Gate', hours: 2.5, reason: 'Client requested extended shift support' },
    { id: '2', guardName: 'Penda Nafuka', siteName: 'Acme HQ', post: 'Warehouse South', hours: 3.0, reason: 'Late guard relief replacement delay' },
  ]);

  const handleAction = (id: string, approved: boolean) => {
    // Optimistic removal
    setRequests((prev) => prev.filter((r) => r.id !== id));
    alert(approved ? 'Overtime authorized' : 'Overtime rejected');
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={requests}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <Card.Content>
              <View style={styles.header}>
                <View style={styles.guardMeta}>
                  <Text style={styles.name}>{item.guardName}</Text>
                  <Text style={styles.site}>{item.siteName} • {item.post}</Text>
                </View>
                <Text style={styles.hours}>{item.hours} hrs</Text>
              </View>
              
              <Text style={styles.reasonTitle}>EXPLANATION NOTE</Text>
              <Text style={styles.reasonText}>{item.reason}</Text>
              
              <View style={styles.btns}>
                <Button
                  mode="outlined"
                  onPress={() => handleAction(item.id, false)}
                  style={styles.btnReject}
                  textColor={Theme.colors.absent}
                >
                  Reject
                </Button>
                <Button
                  mode="contained"
                  onPress={() => handleAction(item.id, true)}
                  style={styles.btnApprove}
                >
                  Approve
                </Button>
              </View>
            </Card.Content>
          </Card>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <MaterialCommunityIcons name="clock-check-outline" size={48} color={Theme.colors.placeholder} />
            <Text style={styles.emptyText}>No pending overtime authorizations.</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    padding: 16,
  },
  list: {
    paddingBottom: 24,
  },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: Theme.colors.accentGold,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  guardMeta: {
    flex: 1,
    marginRight: 8,
  },
  name: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFF',
  },
  site: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    marginTop: 2,
  },
  hours: {
    fontSize: 18,
    fontWeight: 'bold',
    color: Theme.colors.accentGold,
  },
  reasonTitle: {
    fontSize: 9,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    letterSpacing: 0.5,
    marginTop: 4,
  },
  reasonText: {
    fontSize: 13,
    color: Theme.colors.onSurface,
    marginTop: 4,
    fontStyle: 'italic',
  },
  btns: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
    marginTop: 16,
  },
  btnReject: {
    borderColor: Theme.colors.absent,
    borderRadius: 8,
  },
  btnApprove: {
    backgroundColor: Theme.colors.primary,
    borderRadius: 8,
  },
  empty: {
    alignItems: 'center',
    marginTop: 64,
    gap: 12,
  },
  emptyText: {
    color: Theme.colors.placeholder,
    fontSize: 14,
  },
});
