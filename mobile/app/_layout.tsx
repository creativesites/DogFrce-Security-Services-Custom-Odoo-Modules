import React, { useEffect, useRef } from 'react';
import { AppState, AppStateStatus, Platform, StyleSheet, View } from 'react-native';
import { Slot, useRouter, useSegments } from 'expo-router';
import { useAuthStore } from '../src/stores/authStore';
import { registerSessionExpiredHandler } from '../src/api/client';
import { PaperProvider, ActivityIndicator } from 'react-native-paper';
import { Theme } from '../src/theme';
import { StatusBar } from 'react-native';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../src/api/queryClient';
import ErrorBoundary from '../src/components/ErrorBoundary';
import OfflineBanner from '../src/components/OfflineBanner';
import { startNetworkWatcher, initPendingCount } from '../src/utils/networkWatcher';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import apiClient from '../src/api/client';
const LOCK_AFTER_MS = 5 * 60 * 1000;

// Show notification alerts while app is foregrounded
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

async function registerPushToken(): Promise<void> {
  try {
    if (Platform.OS === 'web') return;
    const { status: existing } = await Notifications.getPermissionsAsync();
    let finalStatus = existing;
    if (existing !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== 'granted') return;

    const projectId = Constants.expoConfig?.extra?.eas?.projectId as string | undefined;
    const tokenResult = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined,
    );
    const token = tokenResult.data;
    if (!token) return;

    await apiClient.post('/api/security/mobile/device/token', { token });
  } catch (err) {
    // Non-fatal — push is best-effort
    console.warn('Push token registration:', err);
  }
}

export default function RootLayout() {
  const { isAuthenticated, isLoading, isLocked, user, bootstrap, lock, logout } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();
  const backgroundedAt = useRef<number | null>(null);
  const pushRegistered = useRef(false);

  useEffect(() => {
    bootstrap();
    startNetworkWatcher();
    initPendingCount();
  }, []);

  useEffect(() => {
    registerSessionExpiredHandler(() => {
      // Guard against race: only logout if we're actually authenticated.
      // This prevents in-flight requests from a previous session firing
      // the handler immediately after a new login starts.
      const { isAuthenticated: stillAuth, isLoading: stillLoading } = useAuthStore.getState();
      if (stillAuth && !stillLoading) {
        logout();
      }
    });
  }, [logout]);

  // Register push token once after login
  useEffect(() => {
    if (isAuthenticated && !pushRegistered.current) {
      pushRegistered.current = true;
      registerPushToken();
    }
    if (!isAuthenticated) {
      pushRegistered.current = false;
    }
  }, [isAuthenticated]);

  // Handle notification taps (app opened via notification)
  useEffect(() => {
    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as Record<string, unknown>;
      if (!data) return;
      if (data.type === 'batch_reviewed' && data.site_id) {
        router.push(`/(owner)/site/${data.site_id}`);
      }
    });
    return () => sub.remove();
  }, [router]);

  useEffect(() => {
    const handleAppStateChange = (nextState: AppStateStatus) => {
      if (nextState === 'background' || nextState === 'inactive') {
        backgroundedAt.current = Date.now();
      } else if (nextState === 'active') {
        if (
          backgroundedAt.current !== null &&
          Date.now() - backgroundedAt.current >= LOCK_AFTER_MS &&
          isAuthenticated
        ) {
          lock();
        }
        backgroundedAt.current = null;
      }
    };
    const sub = AppState.addEventListener('change', handleAppStateChange);
    return () => sub.remove();
  }, [isAuthenticated, lock]);

  useEffect(() => {
    if (isLoading) return;
    const segs = segments as string[];
    const inAuthGroup = segs[0] === '(auth)';
    const onLockScreen = segs[0] === '(auth)' && segs[1] === 'lock';

    if (!isAuthenticated) {
      if (!inAuthGroup) router.replace('/(auth)/login');
      return;
    }
    if (isLocked) {
      if (!onLockScreen) router.replace('/(auth)/lock');
      return;
    }
    if (user) {
      const hasCorrectSegment = segs[0] === `(${user.role})`;
      if (!hasCorrectSegment) {
        if (user.role === 'supervisor') router.replace('/(supervisor)');
        else if (user.role === 'manager') router.replace('/(manager)');
        else if (user.role === 'owner') router.replace('/(owner)');
      }
    }
  }, [isAuthenticated, isLoading, isLocked, segments, user]);

  if (isLoading) {
    return (
      <PaperProvider theme={Theme}>
        <View style={styles.loader}>
          <StatusBar barStyle="dark-content" />
          <ActivityIndicator size="large" color={Theme.colors.primary} />
        </View>
      </PaperProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <PaperProvider theme={Theme}>
        <StatusBar barStyle="dark-content" backgroundColor={Theme.colors.background} />
        <OfflineBanner />
        <ErrorBoundary>
          <Slot />
        </ErrorBoundary>
      </PaperProvider>
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
