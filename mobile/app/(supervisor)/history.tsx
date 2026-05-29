import React, { useState } from 'react';
import { View, StyleSheet, FlatList } from 'react-native';
import { Text, Card } from 'react-native-paper';
import { Theme } from '../../src/theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface HistoryItem {
  id: string;
  date: string;
  siteName: string;
  presentCount: number;
  totalCount: number;
  status: 'captured' | 'confirmed';
}

export default function SupervisorHistoryScreen() {
  const [history] = useState<HistoryItem[]>([
    { id: '1', date: '2026-05-28', siteName: 'Acme HQ', presentCount: 8, totalCount: 8, status: 'confirmed' },
    { id: '2', date: '2026-05-27', siteName: 'Acme HQ', presentCount: 7, totalCount: 8, status: 'confirmed' },
    { id: '3', date: '2026-05-26', siteName: 'Acme HQ', presentCount: 8, totalCount: 8, status: 'confirmed' },
    { id: '4', date: '2026-05-25', siteName: 'Acme HQ', presentCount: 6, totalCount: 8, status: 'confirmed' },
  ]);

  return (
    <View style={styles.container}>
      <FlatList
        data={history}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <Card.Content>
              <View style={styles.row}>
                <View style={styles.info}>
                  <Text style={styles.siteName}>{item.siteName}</Text>
                  <Text style={styles.date}>{item.date}</Text>
                </View>
                <View style={styles.rightSec}>
                  <View style={styles.countRow}>
                    <MaterialCommunityIcons name="account-check" size={16} color={Theme.colors.present} />
                    <Text style={styles.countText}>
                      {item.presentCount}/{item.totalCount}
                    </Text>
                  </View>
                  <View style={[styles.badge, item.status === 'confirmed' && styles.confirmedBadge]}>
                    <Text style={styles.badgeText}>{item.status.toUpperCase()}</Text>
                  </View>
                </View>
              </View>
            </Card.Content>
          </Card>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <MaterialCommunityIcons name="history" size={48} color={Theme.colors.placeholder} />
            <Text style={styles.emptyText}>No historical logs available.</Text>
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
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  info: {
    flex: 1,
  },
  siteName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFF',
  },
  date: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    marginTop: 4,
  },
  rightSec: {
    alignItems: 'flex-end',
    gap: 6,
  },
  countRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  countText: {
    fontSize: 13,
    color: Theme.colors.text,
    fontWeight: 'bold',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    backgroundColor: 'rgba(99, 102, 241, 0.15)',
    borderColor: Theme.colors.primary,
    borderWidth: 1,
  },
  confirmedBadge: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    borderColor: Theme.colors.present,
  },
  badgeText: {
    fontSize: 9,
    fontWeight: 'bold',
    color: '#FFF',
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
