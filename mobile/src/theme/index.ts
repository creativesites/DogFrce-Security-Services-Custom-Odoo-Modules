import { MD3LightTheme } from 'react-native-paper';

export const Theme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#4F46E5',
    secondary: '#7C3AED',
    background: '#F8FAFC',
    surface: '#FFFFFF',
    surfaceVariant: '#F1F5F9',
    text: '#0F172A',
    onSurface: '#334155',
    placeholder: '#94A3B8',

    present: '#059669',
    absent: '#DC2626',
    awol: '#D97706',
    late: '#E11D48',
    scheduled: '#2563EB',
    not_marked: '#94A3B8',

    border: '#E2E8F0',
    accentGold: '#D97706',
    accentCyan: '#0891B2',
  },
  roundness: 16,
};
