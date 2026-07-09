import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import Svg, { Rect } from 'react-native-svg';
import { Theme } from '../theme';

interface DataPoint {
  label: string;
  value: number;
}

interface Props {
  data: DataPoint[];
  height?: number;
  barColor?: string;
  labelColor?: string;
  selectedIndex?: number;
  onBarPress?: (index: number) => void;
}

export default function MiniBarChart({
  data,
  height = 64,
  barColor = Theme.colors.primary,
  labelColor = Theme.colors.placeholder,
  selectedIndex,
  onBarPress,
}: Props) {
  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const barWidth = 24;
  const gap = 8;
  const totalWidth = data.length * (barWidth + gap) - gap;

  const hasSelection = selectedIndex !== undefined;

  return (
    <View style={styles.wrapper}>
      <Svg width={totalWidth} height={height}>
        {data.map((d, i) => {
          const barH = Math.max(4, (d.value / maxVal) * height);
          const isSelected = hasSelection ? i === selectedIndex : i === data.length - 1;
          const opacity = isSelected ? 1 : hasSelection ? 0.3 : 0.45;
          return (
            <Rect
              key={i}
              x={i * (barWidth + gap)}
              y={height - barH}
              width={barWidth}
              height={barH}
              rx={4}
              fill={isSelected ? barColor : barColor}
              opacity={opacity}
              onPress={onBarPress ? () => onBarPress(i) : undefined}
            />
          );
        })}
      </Svg>
      <View style={[styles.labels, { width: totalWidth }]}>
        {data.map((d, i) => {
          const isSelected = hasSelection ? i === selectedIndex : i === data.length - 1;
          return (
            <Text
              key={i}
              style={[
                styles.label,
                { color: isSelected ? barColor : labelColor, width: barWidth },
                isSelected && styles.labelSelected,
              ]}
              numberOfLines={1}
            >
              {d.label}
            </Text>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'flex-start',
  },
  labels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  label: {
    fontSize: 8,
    textAlign: 'center',
  },
  labelSelected: {
    fontWeight: 'bold',
  },
});
