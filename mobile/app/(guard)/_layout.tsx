import React from 'react';
import { Tabs } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../../src/theme';

export default function GuardLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: Theme.colors.surface },
        headerTitleStyle: { fontWeight: '700', color: Theme.colors.text },
        tabBarStyle: { backgroundColor: Theme.colors.surface, borderTopColor: Theme.colors.border },
        tabBarActiveTintColor: Theme.colors.primary,
        tabBarInactiveTintColor: Theme.colors.placeholder,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'My Shift',
          headerTitle: 'Guard Duty Portal',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="shield-account" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="patrol"
        options={{
          title: 'Patrol Log',
          headerTitle: 'Patrol & Site Notes',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="clipboard-text-clock-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: 'My Attendance',
          headerTitle: '30-Day Attendance Record',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="calendar-check-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          headerTitle: 'Guard Profile & Settings',
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="account-circle-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
