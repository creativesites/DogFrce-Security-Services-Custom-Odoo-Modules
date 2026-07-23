import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { Theme } from '../theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface KpiMetricProps {
  title: string;
  value: string | number;
  icon: React.ComponentProps<typeof MaterialCommunityIcons>['name'];
  color?: string;
  subtitle?: string;
}

export const KpiMetric: React.FC<KpiMetricProps> = ({
  title,
  value,
  icon,
  color = Theme.colors.primary,
  subtitle,
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        <View style={[styles.iconWrapper, { backgroundColor: `${color}15` }]}>
          <MaterialCommunityIcons name={icon} size={20} color={color} />
        </View>
      </View>
      
      <Text style={styles.value} numberOfLines={1}>{value}</Text>
      
      {subtitle && (
        <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    flex: 1,
    minWidth: 140,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    fontSize: 12,
    fontWeight: 'bold',
    color: Theme.colors.placeholder,
    flex: 1,
    marginRight: 4,
  },
  iconWrapper: {
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  value: {
    fontSize: 22,
    fontWeight: 'bold',
    color: Theme.colors.text,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 10,
    color: Theme.colors.placeholder,
    marginTop: 4,
  },
});
export default KpiMetric;
