import React, { useEffect, useState } from 'react';
import { View, StyleSheet, Image } from 'react-native';
import { Text, Button } from 'react-native-paper';
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuthStore } from '../../src/stores/authStore';
import { Theme } from '../../src/theme';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function LockScreen() {
  const { user, unlock, logout } = useAuthStore();
  const router = useRouter();
  const [error, setError] = useState('');
  const [authenticating, setAuthenticating] = useState(false);

  const attempt = async () => {
    setAuthenticating(true);
    setError('');
    try {
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = await LocalAuthentication.isEnrolledAsync();

      if (!hasHardware || !isEnrolled) {
        // Device has no biometrics — skip lock entirely
        unlock();
        return;
      }

      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Verify your identity to continue',
        cancelLabel: 'Sign out instead',
        disableDeviceFallback: false,
      });

      if (result.success) {
        unlock();
      } else if (result.error === 'user_cancel') {
        // User explicitly chose "Sign out instead"
        await logout();
      } else {
        setError('Biometric check failed. Please try again.');
      }
    } catch (err) {
      setError('Authentication error. Try again.');
    } finally {
      setAuthenticating(false);
    }
  };

  // Attempt automatically on mount
  useEffect(() => {
    attempt();
  }, []);

  return (
    <View style={styles.container}>
      <Image
        source={require('../../assets/deployguard.png')}
        style={styles.logo}
        resizeMode="contain"
      />

      <View style={styles.lockBadge}>
        <MaterialCommunityIcons name="lock-outline" size={32} color={Theme.colors.primary} />
      </View>

      <Text style={styles.heading}>App Locked</Text>
      <Text style={styles.sub}>
        {user?.name ? `Welcome back, ${user.name.split(' ')[0]}` : 'Verify your identity to continue'}
      </Text>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <Button
        mode="contained"
        onPress={attempt}
        loading={authenticating}
        disabled={authenticating}
        style={styles.btn}
        labelStyle={styles.btnLabel}
        icon="fingerprint"
      >
        Unlock with Biometrics
      </Button>

      <Button
        mode="text"
        onPress={logout}
        style={styles.signOutBtn}
        textColor={Theme.colors.placeholder}
      >
        Sign out
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Theme.colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  logo: {
    width: 72,
    height: 72,
    borderRadius: 18,
    marginBottom: 24,
  },
  lockBadge: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: `${Theme.colors.primary}12`,
    borderWidth: 1.5,
    borderColor: Theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  heading: {
    fontSize: 24,
    fontWeight: 'bold',
    color: Theme.colors.text,
    marginBottom: 8,
  },
  sub: {
    fontSize: 14,
    color: Theme.colors.placeholder,
    textAlign: 'center',
    marginBottom: 32,
  },
  errorText: {
    color: Theme.colors.absent,
    fontSize: 13,
    marginBottom: 16,
    textAlign: 'center',
  },
  btn: {
    width: '100%',
    borderRadius: 14,
    paddingVertical: 4,
    marginBottom: 16,
  },
  btnLabel: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  signOutBtn: {
    marginTop: 4,
  },
});
