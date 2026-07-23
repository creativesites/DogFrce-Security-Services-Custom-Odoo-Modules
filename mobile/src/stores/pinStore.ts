import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import * as LocalAuthentication from 'expo-local-authentication';

const PIN_STORE_KEY = '@deployguard_user_pin';
const PIN_ENABLED_KEY = '@deployguard_pin_enabled';

interface PinState {
  isPinSet: boolean;
  isPinLocked: boolean;
  hasBiometrics: boolean;
  setupPin: (pin: string) => Promise<void>;
  verifyPin: (pin: string) => Promise<boolean>;
  clearPin: () => Promise<void>;
  authenticateBiometric: () => Promise<boolean>;
  setPinLocked: (locked: boolean) => void;
  initPinStore: () => Promise<void>;
}

export const usePinStore = create<PinState>((set, get) => ({
  isPinSet: false,
  isPinLocked: false,
  hasBiometrics: false,

  initPinStore: async () => {
    try {
      const storedPin = await SecureStore.getItemAsync(PIN_STORE_KEY);
      const isEnabled = await SecureStore.getItemAsync(PIN_ENABLED_KEY);
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = await LocalAuthentication.isEnrolledAsync();

      const isSet = !!storedPin && isEnabled === 'true';
      set({
        isPinSet: isSet,
        isPinLocked: isSet, // Default to locked if PIN is configured
        hasBiometrics: hasHardware && isEnrolled,
      });
    } catch (err) {
      console.warn('[PinStore] Error initializing PIN store:', err);
    }
  },

  setupPin: async (pin: string) => {
    try {
      await SecureStore.setItemAsync(PIN_STORE_KEY, pin);
      await SecureStore.setItemAsync(PIN_ENABLED_KEY, 'true');
      set({ isPinSet: true, isPinLocked: false });
    } catch (err) {
      console.warn('[PinStore] Failed to set PIN:', err);
    }
  },

  verifyPin: async (pin: string) => {
    try {
      const storedPin = await SecureStore.getItemAsync(PIN_STORE_KEY);
      if (storedPin === pin) {
        set({ isPinLocked: false });
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },

  clearPin: async () => {
    try {
      await SecureStore.deleteItemAsync(PIN_STORE_KEY);
      await SecureStore.deleteItemAsync(PIN_ENABLED_KEY);
      set({ isPinSet: false, isPinLocked: false });
    } catch (err) {
      console.warn('[PinStore] Failed to clear PIN:', err);
    }
  },

  authenticateBiometric: async () => {
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Unlock DeployGuard',
        fallbackLabel: 'Use PIN',
        cancelLabel: 'Cancel',
      });
      if (result.success) {
        set({ isPinLocked: false });
        return true;
      }
      return false;
    } catch (err) {
      console.warn('[PinStore] Biometric auth error:', err);
      return false;
    }
  },

  setPinLocked: (locked: boolean) => set({ isPinLocked: locked }),
}));
