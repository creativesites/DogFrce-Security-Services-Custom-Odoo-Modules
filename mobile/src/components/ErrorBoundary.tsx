import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../theme';

interface Props {
  children: React.ReactNode;
  fallbackLabel?: string;
}

interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message || 'An unexpected error occurred.' };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
    // TODO: wire up a crash reporter here when Sentry is compatible with Expo SDK 54
  }

  reset = () => this.setState({ hasError: false, message: '' });

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <View style={styles.container}>
        <MaterialCommunityIcons name="alert-circle-outline" size={48} color={Theme.colors.absent} />
        <Text style={styles.heading}>Something went wrong</Text>
        <Text style={styles.message}>{this.state.message}</Text>
        <TouchableOpacity style={styles.btn} onPress={this.reset}>
          <MaterialCommunityIcons name="refresh" size={18} color="#FFF" />
          <Text style={styles.btnLabel}>{this.props.fallbackLabel ?? 'Reload Screen'}</Text>
        </TouchableOpacity>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Theme.colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
    gap: 16,
  },
  heading: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Theme.colors.text,
  },
  message: {
    fontSize: 13,
    color: Theme.colors.placeholder,
    textAlign: 'center',
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: Theme.colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 8,
  },
  btnLabel: {
    color: '#FFF',
    fontWeight: '600',
    fontSize: 14,
  },
});
