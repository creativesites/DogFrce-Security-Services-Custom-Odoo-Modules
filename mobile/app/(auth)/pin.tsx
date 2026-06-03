import React, { useState } from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text, Button, ActivityIndicator } from 'react-native-paper';
import { useRouter } from 'expo-router';
import * as Crypto from 'expo-crypto';
import { authenticateWithPin } from '../../src/api/pin';
import { useAuthStore } from '../../src/stores/authStore';
import { Theme } from '../../src/theme';

const PIN_LENGTH = 4;
const DIAL_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫'];

export default function PinScreen() {
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();
  const { user, setSession } = useAuthStore();

  const handleKey = (key: string) => {
    if (key === '⌫') {
      setPin(p => p.slice(0, -1));
      setError('');
    } else if (pin.length < PIN_LENGTH) {
      const next = pin + key;
      setPin(next);
      if (next.length === PIN_LENGTH) {
        submitPin(next);
      }
    }
  };

  const submitPin = async (value: string) => {
    if (!user?.employee_id) {
      setError('No employee linked. Please log in with password.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      // Hash the PIN before sending
      const hash = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        value
      );
      const result = await authenticateWithPin(user.employee_id, hash, user.db);
      await setSession(result.session_id, user);
      router.replace('/(supervisor)');
    } catch (err: any) {
      setError(err.message || 'Incorrect PIN. Try again.');
      setPin('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Quick Access</Text>
        <Text style={styles.subtitle}>
          {user?.name ? `Welcome back, ${user.name.split(' ')[0]}` : 'Enter your PIN'}
        </Text>
      </View>

      {/* PIN dots */}
      <View style={styles.dotsRow}>
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <View key={i} style={[styles.dot, i < pin.length && styles.dotFilled]} />
        ))}
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {loading ? (
        <ActivityIndicator color={Theme.colors.primary} style={{ marginTop: 24 }} />
      ) : (
        <View style={styles.dialpad}>
          {DIAL_KEYS.map((key, i) => (
            key === '' ? (
              <View key={i} style={styles.dialEmpty} />
            ) : (
              <TouchableOpacity
                key={i}
                style={styles.dialKey}
                onPress={() => handleKey(key)}
                activeOpacity={0.7}
              >
                <Text style={styles.dialText}>{key}</Text>
              </TouchableOpacity>
            )
          ))}
        </View>
      )}

      <Button
        mode="text"
        onPress={() => router.replace('/(auth)/login')}
        style={styles.switchBtn}
        labelStyle={{ color: Theme.colors.placeholder }}
      >
        Use password instead
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0B0B0F', justifyContent: 'center', alignItems: 'center', padding: 32 },
  header: { alignItems: 'center', marginBottom: 40 },
  title: { fontSize: 28, fontWeight: '700', color: '#FFF' },
  subtitle: { fontSize: 14, color: Theme.colors.placeholder, marginTop: 6 },
  dotsRow: { flexDirection: 'row', gap: 16, marginBottom: 16 },
  dot: { width: 16, height: 16, borderRadius: 8, borderWidth: 2, borderColor: Theme.colors.placeholder },
  dotFilled: { backgroundColor: Theme.colors.primary, borderColor: Theme.colors.primary },
  error: { color: Theme.colors.absent, fontSize: 13, marginBottom: 16 },
  dialpad: { flexDirection: 'row', flexWrap: 'wrap', width: 240, gap: 16, marginTop: 24 },
  dialKey: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#1E1E2E',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2A2A3E',
  },
  dialText: { fontSize: 22, fontWeight: '600', color: '#FFF' },
  dialEmpty: { width: 64, height: 64 },
  switchBtn: { marginTop: 32 },
});
