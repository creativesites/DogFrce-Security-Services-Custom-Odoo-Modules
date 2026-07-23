import React from 'react';
import { View, StyleSheet, ScrollView, Alert } from 'react-native';
import { Text, Button, List, Card, Divider } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../../src/theme';
import { useAuthStore } from '../../src/stores/authStore';
import { usePinStore } from '../../src/stores/pinStore';

export default function GuardProfileScreen() {
  const { user, logout, serverUrl } = useAuthStore();
  const { isPinSet } = usePinStore();

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to log out of DeployGuard?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: () => logout(),
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Card style={styles.card}>
        <Card.Content style={styles.cardContent}>
          <View style={styles.header}>
            <View style={styles.avatar}>
              <MaterialCommunityIcons name="account" size={36} color={Theme.colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.name}>{user?.name || 'Guard User'}</Text>
              <Text style={styles.roleText}>Role: Security Guard</Text>
            </View>
          </View>

          <Divider style={styles.divider} />

          <List.Item
            title="Username"
            description={user?.username || '—'}
            left={(props) => <List.Icon {...props} icon="account-details-outline" />}
          />
          <List.Item
            title="Database"
            description={user?.db || 'dogforce_dev'}
            left={(props) => <List.Icon {...props} icon="database-outline" />}
          />
          <List.Item
            title="Server URL"
            description={serverUrl}
            left={(props) => <List.Icon {...props} icon="server-network" />}
          />
          <List.Item
            title="Quick Lock Status"
            description={isPinSet ? '4-Digit Security PIN Configured' : 'No Security PIN Configured'}
            left={(props) => <List.Icon {...props} icon="shield-lock-outline" />}
          />

          <Divider style={styles.divider} />

          <Button
            mode="outlined"
            icon="logout"
            onPress={handleLogout}
            style={styles.logoutBtn}
            labelStyle={{ color: Theme.colors.absent, fontWeight: '700' }}
          >
            LOGOUT
          </Button>
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  content: { padding: 16 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    elevation: 0,
  },
  cardContent: { padding: 16 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: `${Theme.colors.primary}15`,
    justifyContent: 'center',
    alignItems: 'center',
  },
  name: { fontSize: 18, fontWeight: '700', color: Theme.colors.text },
  roleText: { fontSize: 12, color: Theme.colors.placeholder, marginTop: 2 },
  divider: { marginVertical: 12 },
  logoutBtn: { borderColor: Theme.colors.absent, borderRadius: 12, marginTop: 8 },
});
