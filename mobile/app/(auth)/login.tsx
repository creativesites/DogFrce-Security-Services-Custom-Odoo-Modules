import React, { useRef, useState } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Image,
  TouchableOpacity,
  TextInput as RNTextInput,
} from 'react-native';
import { Text, TextInput, Button, HelperText, ActivityIndicator } from 'react-native-paper';
import { useAuthStore } from '../../src/stores/authStore';
import { Theme } from '../../src/theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const DEMO_DB = process.env.EXPO_PUBLIC_ODOO_DB || 'dogforce_dev';
// Show demo access chips unless explicitly disabled via EXPO_PUBLIC_SHOW_DEMO=false.
const SHOW_DEMO = process.env.EXPO_PUBLIC_SHOW_DEMO !== 'false';

const DEMO_CHIPS = [
  { label: 'Owner',      color: '#4F46E5', username: 'demo.admin@dogforce.demo',    password: 'Demo2026!' },
  { label: 'Manager',    color: '#7C3AED', username: 'demo.manager@dogforce.demo',  password: 'Demo2026!' },
  { label: 'Supervisor', color: '#0891B2', username: 'demo.operator@dogforce.demo', password: 'Demo2026!' },
] as const;

export default function LoginScreen() {
  const [db, setDb] = useState(DEMO_DB);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [chipLoading, setChipLoading] = useState<string | null>(null);

  const { login, serverUrl, setServerUrl } = useAuthStore();
  const [urlInput, setUrlInput] = useState(serverUrl);
  const passwordRef = useRef<RNTextInput>(null);

  const handleLogin = async () => {
    if (!username.trim() || !password) {
      setErrorMsg('Please enter your username and password.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    try {
      if (urlInput.trim() && urlInput.trim() !== serverUrl) {
        await setServerUrl(urlInput.trim());
      }
      await login(db, username.trim(), password);
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChipLogin = async (chip: (typeof DEMO_CHIPS)[number]) => {
    setChipLoading(chip.label);
    setErrorMsg('');
    try {
      await login(DEMO_DB, chip.username, chip.password);
    } catch (err: any) {
      setErrorMsg(`Demo login failed: ${err.message || 'Check server connection.'}`);
    } finally {
      setChipLoading(null);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
        <View style={styles.logoSec}>
          <Image
            source={require('../../assets/deployguard.png')}
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={styles.title}>DeployGuard</Text>
          <Text style={styles.subtitle}>Field Attendance Platform</Text>
        </View>

        {SHOW_DEMO && (
          <View style={styles.demoSection}>
            <Text style={styles.demoLabel}>Demo access</Text>
            <View style={styles.demoRow}>
              {DEMO_CHIPS.map((chip) => {
                const isThisLoading = chipLoading === chip.label;
                return (
                  <TouchableOpacity
                    key={chip.label}
                    style={[
                      styles.demoChip,
                      { borderColor: chip.color, backgroundColor: `${chip.color}10` },
                      chipLoading && styles.demoChipDisabled,
                    ]}
                    onPress={() => handleChipLogin(chip)}
                    disabled={!!chipLoading || loading}
                    activeOpacity={0.75}
                  >
                    {isThisLoading ? (
                      <ActivityIndicator size={12} color={chip.color} />
                    ) : (
                      <Text style={[styles.demoChipLabel, { color: chip.color }]}>{chip.label}</Text>
                    )}
                  </TouchableOpacity>
                );
              })}
            </View>
            <Text style={styles.demoHint}>Signs in with live demo credentials</Text>
          </View>
        )}

        <View style={styles.form}>
          <Text style={styles.loginHeader}>Sign In</Text>

          {errorMsg ? (
            <HelperText type="error" visible style={styles.errorText}>
              {errorMsg}
            </HelperText>
          ) : null}

          <TextInput
            label="Username / Email"
            value={username}
            onChangeText={setUsername}
            mode="outlined"
            autoCapitalize="none"
            keyboardType="email-address"
            returnKeyType="next"
            onSubmitEditing={() => passwordRef.current?.focus()}
            blurOnSubmit={false}
            style={styles.input}
            outlineColor={Theme.colors.border}
            activeOutlineColor={Theme.colors.primary}
          />

          <TextInput
            ref={passwordRef as any}
            label="Password"
            value={password}
            onChangeText={setPassword}
            mode="outlined"
            secureTextEntry={!showPassword}
            returnKeyType="go"
            onSubmitEditing={handleLogin}
            style={styles.input}
            outlineColor={Theme.colors.border}
            activeOutlineColor={Theme.colors.primary}
            right={
              <TextInput.Icon
                icon={showPassword ? 'eye-off-outline' : 'eye-outline'}
                onPress={() => setShowPassword((v) => !v)}
                color={Theme.colors.placeholder}
              />
            }
          />

          <Button
            mode="contained"
            onPress={handleLogin}
            loading={loading}
            disabled={loading || !!chipLoading}
            style={styles.button}
            labelStyle={styles.buttonLabel}
          >
            Sign In
          </Button>

          <TouchableOpacity
            style={styles.advancedToggle}
            onPress={() => setShowAdvanced((v) => !v)}
            activeOpacity={0.7}
          >
            <MaterialCommunityIcons
              name={showAdvanced ? 'chevron-up' : 'chevron-down'}
              size={16}
              color={Theme.colors.placeholder}
            />
            <Text style={styles.advancedLabel}>Advanced</Text>
          </TouchableOpacity>

          {showAdvanced && (
            <View style={styles.advancedSection}>
              <TextInput
                label="Server URL"
                value={urlInput}
                onChangeText={setUrlInput}
                mode="outlined"
                autoCapitalize="none"
                autoCorrect={false}
                style={styles.input}
                outlineColor={Theme.colors.border}
                activeOutlineColor={Theme.colors.primary}
                placeholder="http://your-server:8069"
              />
              <TextInput
                label="Database"
                value={db}
                onChangeText={setDb}
                mode="outlined"
                autoCapitalize="none"
                autoCorrect={false}
                style={styles.input}
                outlineColor={Theme.colors.border}
                activeOutlineColor={Theme.colors.primary}
              />
              <Text style={styles.advancedHint}>
                Only change these when connecting to a different DeployGuard instance.
              </Text>
            </View>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Theme.colors.background,
  },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  logoSec: {
    alignItems: 'center',
    marginBottom: 28,
  },
  logo: {
    width: 80,
    height: 80,
    borderRadius: 20,
    marginBottom: 14,
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: Theme.colors.text,
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 13,
    color: Theme.colors.placeholder,
    marginTop: 4,
    letterSpacing: 0.5,
  },
  demoSection: {
    marginBottom: 24,
    alignItems: 'center',
  },
  demoLabel: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 10,
  },
  demoRow: {
    flexDirection: 'row',
    gap: 10,
    justifyContent: 'center',
  },
  demoChip: {
    paddingHorizontal: 16,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1.5,
    minWidth: 84,
    alignItems: 'center',
    justifyContent: 'center',
  },
  demoChipDisabled: { opacity: 0.5 },
  demoChipLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  demoHint: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    marginTop: 8,
    opacity: 0.7,
  },
  form: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  loginHeader: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Theme.colors.text,
    marginBottom: 20,
  },
  input: {
    backgroundColor: Theme.colors.background,
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
  advancedToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    marginTop: 20,
    paddingVertical: 4,
  },
  advancedLabel: {
    fontSize: 12,
    color: Theme.colors.placeholder,
    fontWeight: '600',
  },
  advancedSection: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: Theme.colors.border,
  },
  advancedHint: {
    fontSize: 11,
    color: Theme.colors.placeholder,
    textAlign: 'center',
    marginTop: -8,
    marginBottom: 4,
  },
});
