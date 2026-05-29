import React, { useState } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, Image } from 'react-native';
import { Text, TextInput, Button, HelperText } from 'react-native-paper';
import { useAuthStore } from '../../src/stores/authStore';
import { Theme } from '../../src/theme';
import { useRouter } from 'expo-router';

export default function LoginScreen() {
  const [db, setDb] = useState('dogforce_prod');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  const login = useAuthStore((state) => state.login);
  const router = useRouter();

  const handleLogin = async () => {
    if (!username || !password) {
      setErrorMsg('Please enter both your username and password.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    try {
      await login(db, username, password);
      // Auth guard in root layout will handle redirect based on role
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.logoSec}>
          <Image
            source={{ uri: 'https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&q=80&w=200&h=200' }}
            style={styles.logo}
          />
          <Text style={styles.title}>DOGFORCE</Text>
          <Text style={styles.subtitle}>Security Services Suite</Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.loginHeader}>Sign In</Text>

          {errorMsg ? (
            <HelperText type="error" visible={true} style={styles.errorText}>
              {errorMsg}
            </HelperText>
          ) : null}

          <TextInput
            label="Odoo Database"
            value={db}
            onChangeText={setDb}
            mode="outlined"
            style={styles.input}
            outlineColor={Theme.colors.border}
            activeOutlineColor={Theme.colors.primary}
            textColor={Theme.colors.text}
          />

          <TextInput
            label="Username / Email"
            value={username}
            onChangeText={setUsername}
            mode="outlined"
            autoCapitalize="none"
            style={styles.input}
            outlineColor={Theme.colors.border}
            activeOutlineColor={Theme.colors.primary}
            textColor={Theme.colors.text}
          />

          <TextInput
            label="Password"
            value={password}
            onChangeText={setPassword}
            mode="outlined"
            secureTextEntry
            style={styles.input}
            outlineColor={Theme.colors.border}
            activeOutlineColor={Theme.colors.primary}
            textColor={Theme.colors.text}
          />

          <Button
            mode="contained"
            onPress={handleLogin}
            loading={loading}
            disabled={loading}
            style={styles.button}
            labelStyle={styles.buttonLabel}
          >
            Authenticate
          </Button>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0B0F',
  },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  logoSec: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logo: {
    width: 90,
    height: 90,
    borderRadius: 45,
    marginBottom: 16,
    borderWidth: 2,
    borderColor: Theme.colors.primary,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFF',
    letterSpacing: 2,
  },
  subtitle: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    marginTop: 4,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  form: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: 24,
  },
  loginHeader: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
    marginBottom: 20,
  },
  input: {
    backgroundColor: 'transparent',
    marginBottom: 16,
  },
  button: {
    marginTop: 8,
    paddingVertical: 6,
    borderRadius: 12,
  },
  buttonLabel: {
    fontWeight: 'bold',
    fontSize: 16,
  },
  errorText: {
    textAlign: 'center',
    fontSize: 13,
    marginBottom: 12,
  },
});
