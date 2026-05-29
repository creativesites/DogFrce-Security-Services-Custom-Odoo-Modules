import { MD3DarkTheme } from 'react-native-paper';

export const Theme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: '#6366F1', // Indigo Accent
    secondary: '#8B5CF6', // Purple Accent
    background: '#0B0B0F', // Ultra deep charcoal/black
    surface: '#151521', // Dark card surface with a hint of purple/blue
    surfaceVariant: '#222235', // Accent surface
    text: '#F3F4F6', // Off-white
    onSurface: '#E5E7EB',
    placeholder: '#9CA3AF',
    
    // Status colors (tailored gradients and badge colors)
    present: '#10B981', // Jade/Emerald Green
    absent: '#EF4444', // Crimson/Red
    awol: '#F59E0B', // Golden Amber
    late: '#F43F5E', // Rose/Pinkish red
    scheduled: '#3B82F6', // Blue
    not_marked: '#6B7280', // Grey
    
    border: '#2E2E42',
    accentGold: '#FBBF24',
    accentCyan: '#06B6D4'
  },
  roundness: 16,
};
