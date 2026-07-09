import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAppStore } from '../stores/appStore';
import { Theme } from '../theme';

function timeAgo(isoString: string | null): string {
  if (!isoString) return '';
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

type BannerVariant = 'offline' | 'syncing' | 'done' | 'error' | 'none';

function getVariant(isOffline: boolean, syncStatus: string): BannerVariant {
  if (!isOffline && syncStatus === 'idle') return 'none';
  if (!isOffline && syncStatus === 'done') return 'done';
  if (syncStatus === 'syncing') return 'syncing';
  if (isOffline) return 'offline';
  if (syncStatus === 'error') return 'error';
  return 'none';
}

const BG: Record<BannerVariant, string> = {
  none: 'transparent',
  offline: '#DC2626',
  syncing: Theme.colors.accentGold,
  done: Theme.colors.present,
  error: '#7C3AED',
};

const ICON: Record<BannerVariant, string> = {
  none: '',
  offline: 'wifi-off',
  syncing: 'cloud-sync-outline',
  done: 'check-circle-outline',
  error: 'alert-outline',
};

export default function OfflineBanner() {
  const { isOffline, syncStatus, pendingQueueCount, lastSyncedAt, setSyncStatus } = useAppStore();
  const variant = getVariant(isOffline, syncStatus);
  const slideAnim = useRef(new Animated.Value(-40)).current;
  const prevVariantRef = useRef<BannerVariant>('none');
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const prev = prevVariantRef.current;
    prevVariantRef.current = variant;
    if (variant !== 'none' && prev === 'none') {
      Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, tension: 80, friction: 12 }).start();
    } else if (variant === 'none' && prev !== 'none') {
      Animated.timing(slideAnim, { toValue: -40, duration: 220, useNativeDriver: true }).start();
    }
  }, [variant]);

  // Auto-dismiss the "back online" confirmation after 3 s
  useEffect(() => {
    if (dismissTimer.current) clearTimeout(dismissTimer.current);
    if (variant === 'done') {
      dismissTimer.current = setTimeout(() => setSyncStatus('idle'), 3000);
    }
    return () => { if (dismissTimer.current) clearTimeout(dismissTimer.current); };
  }, [variant]);

  if (variant === 'none') return null;

  const label = (): string => {
    switch (variant) {
      case 'offline':
        return [
          'No connection',
          pendingQueueCount > 0 ? ` · ${pendingQueueCount} mark${pendingQueueCount !== 1 ? 's' : ''} queued` : '',
          lastSyncedAt ? ` · last sync ${timeAgo(lastSyncedAt)}` : '',
        ].join('');
      case 'syncing':
        return `Syncing ${pendingQueueCount} pending mark${pendingQueueCount !== 1 ? 's' : ''}…`;
      case 'done':
        return 'Back online — data synced';
      case 'error':
        return 'Sync failed — will retry when online';
      default:
        return '';
    }
  };

  return (
    <Animated.View style={[styles.banner, { backgroundColor: BG[variant], transform: [{ translateY: slideAnim }] }]}>
      <MaterialCommunityIcons name={ICON[variant] as any} size={14} color="#fff" />
      <Text style={styles.text}>{label()}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 7,
    paddingHorizontal: 16,
    overflow: 'hidden',
  },
  text: { color: '#fff', fontSize: 12, fontWeight: '600', flex: 1 },
});
