import React from 'react';
import { Tabs } from 'expo-router';
import { Theme } from '../../src/theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuthStore } from '../../src/stores/authStore';
import { TouchableOpacity, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function SupervisorLayout() {
  const logout = useAuthStore((state) => state.logout);
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        tabBarStyle: [styles.tabBar, { height: 56 + insets.bottom, paddingBottom: 6 + insets.bottom }],
        tabBarActiveTintColor: Theme.colors.primary,
        tabBarInactiveTintColor: Theme.colors.placeholder,
        headerStyle: styles.header,
        headerTitleStyle: styles.headerTitle,
        headerTintColor: Theme.colors.text,
        headerRight: () => (
          <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
            <MaterialCommunityIcons name="logout" size={20} color={Theme.colors.absent} />
          </TouchableOpacity>
        ),
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Sites',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="office-building-marker-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: 'History',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="history" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="site/[siteId]"
        options={{
          href: null,
          title: 'Posting Sheet',
          headerShown: true,
        }}
      />
      <Tabs.Screen
        name="mark/[recordId]"
        options={{
          href: null,
          title: 'Mark Guard',
          headerShown: true,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: Theme.colors.surface,
    borderTopColor: Theme.colors.border,
    paddingTop: 6,
  },
  header: {
    backgroundColor: Theme.colors.surface,
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    elevation: 0,
    shadowOpacity: 0,
  },
  headerTitle: {
    fontWeight: 'bold',
    fontSize: 18,
    color: Theme.colors.text,
  },
  logoutBtn: {
    marginRight: 16,
    padding: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(220, 38, 38, 0.08)',
  },
});
