import React, { useState, useEffect } from 'react';
import { Modal, View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { usePinStore } from '../stores/pinStore';
import { Theme } from '../theme';

export default function PinLockModal() {
  const { isPinSet, isPinLocked, hasBiometrics, verifyPin, authenticateBiometric } = usePinStore();
  const [pin, setPin] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (isPinLocked && hasBiometrics) {
      authenticateBiometric().catch(() => {});
    }
  }, [isPinLocked, hasBiometrics]);

  if (!isPinSet || !isPinLocked) return null;

  const handleKeyPress = async (val: string) => {
    if (pin.length >= 6) return;
    const newPin = pin + val;
    setPin(newPin);
    setErrorMsg('');

    if (newPin.length >= 4) {
      const isValid = await verifyPin(newPin);
      if (!isValid && newPin.length === 6) {
        setErrorMsg('Invalid PIN code. Please try again.');
        setPin('');
      } else if (!isValid && newPin.length < 6) {
        // Allow trying up to 6 digits or auto-clear if 4 digits wrong
        setTimeout(async () => {
          const tryFour = await verifyPin(newPin);
          if (!tryFour) {
            setErrorMsg('Invalid PIN code');
            setPin('');
          }
        }, 300);
      }
    }
  };

  const handleDelete = () => {
    setPin((prev) => prev.slice(0, -1));
    setErrorMsg('');
  };

  return (
    <Modal visible={isPinLocked} animationType="fade" transparent={false}>
      <View style={styles.container}>
        <View style={styles.header}>
          <MaterialCommunityIcons name="shield-lock" size={56} color={Theme.colors.accentGold} />
          <Text style={styles.title}>DeployGuard Secured</Text>

          <View style={styles.pinDotsContainer}>
            {[0, 1, 2, 3].map((idx) => (
              <View
                key={idx}
                style={[
                  styles.pinDot,
                  pin.length > idx && styles.pinDotFilled,
                ]}
              />
            ))}
          </View>

          {errorMsg ? <Text style={styles.errorText}>{errorMsg}</Text> : null}
        </View>

        <View style={styles.keypad}>
          {[['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9']].map((row, rIdx) => (
            <View key={rIdx} style={styles.keypadRow}>
              {row.map((num) => (
                <TouchableOpacity
                  key={num}
                  style={styles.keyBtn}
                  onPress={() => handleKeyPress(num)}
                  activeOpacity={0.6}
                >
                  <Text style={styles.keyText}>{num}</Text>
                </TouchableOpacity>
              ))}
            </View>
          ))}

          <View style={styles.keypadRow}>
            {hasBiometrics ? (
              <TouchableOpacity
                style={styles.keyBtnSpecial}
                onPress={() => authenticateBiometric()}
              >
                <MaterialCommunityIcons name="fingerprint" size={28} color={Theme.colors.accentGold} />
              </TouchableOpacity>
            ) : (
              <View style={styles.keyBtnSpecial} />
            )}

            <TouchableOpacity
              style={styles.keyBtn}
              onPress={() => handleKeyPress('0')}
              activeOpacity={0.6}
            >
              <Text style={styles.keyText}>0</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.keyBtnSpecial}
              onPress={handleDelete}
              activeOpacity={0.6}
            >
              <MaterialCommunityIcons name="backspace-outline" size={24} color="#9CA3AF" />
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
    justifyContent: 'space-between',
    paddingVertical: 60,
    paddingHorizontal: 24,
  },
  header: {
    alignItems: 'center',
    marginTop: 40,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 22,
    fontWeight: '700',
    marginTop: 16,
  },
  pinDotsContainer: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 32,
  },
  pinDot: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#475569',
  },
  pinDotFilled: {
    backgroundColor: Theme.colors.accentGold,
    borderColor: Theme.colors.accentGold,
  },
  errorText: {
    color: '#EF4444',
    fontSize: 13,
    fontWeight: '600',
    marginTop: 16,
  },
  keypad: {
    width: '100%',
    maxWidth: 320,
    alignSelf: 'center',
    gap: 16,
    marginBottom: 20,
  },
  keypadRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  keyBtn: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#1E293B',
    alignItems: 'center',
    justifyContent: 'center',
  },
  keyBtnSpecial: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  keyText: {
    color: '#F8FAFC',
    fontSize: 26,
    fontWeight: '600',
  },
});
