import React, { useEffect } from 'react';
import { Slot, useRouter, useSegments } from 'expo-router';
import { useAuthStore } from '../src/stores/authStore';
import { PaperProvider, ActivityIndicator } from 'react-native-paper';
import { Theme } from '../src/theme';
import { View, StyleSheet, StatusBar } from 'react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

export default function RootLayout() {
  const { isAuthenticated, isLoading, user, bootstrap } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();

  // Run bootstrap on mount to load session
  useEffect(() => {
    bootstrap();
  }, []);

  // Monitor auth status and segment changes to enforce authorization
  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';
    
    if (!isAuthenticated) {
      // Redirect to login if not authenticated
      if (!inAuthGroup) {
        router.replace('/(auth)/login');
      }
    } else if (user) {
      // If authenticated, make sure they go to their respective portal
      const currentRoleSegment = `(${user.role})`;
      const hasCorrectSegment = segments[0] === currentRoleSegment;

      if (!hasCorrectSegment && inAuthGroup) {
        // Automatically send to portal index
        if (user.role === 'supervisor') router.replace('/(supervisor)');
        else if (user.role === 'manager') router.replace('/(manager)');
        else if (user.role === 'owner') router.replace('/(owner)');
      }
    }
  }, [isAuthenticated, isLoading, segments, user]);

  if (isLoading) {
    return (
      <PaperProvider theme={Theme}>
        <View style={styles.loader}>
          <StatusBar barStyle="light-content" />
          <ActivityIndicator size="large" color={Theme.colors.primary} />
        </View>
      </PaperProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <PaperProvider theme={Theme}>
        <StatusBar barStyle="light-content" />
        <Slot />
      </PaperProvider>
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
