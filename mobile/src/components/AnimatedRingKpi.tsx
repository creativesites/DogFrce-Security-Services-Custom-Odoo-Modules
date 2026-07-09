import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated } from 'react-native';
import { Text } from 'react-native-paper';
import Svg, { Circle, G } from 'react-native-svg';
import { Theme } from '../theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

interface Props {
  title: string;
  percent: number;        // 0–100
  icon: string;
  color?: string;
  subtitle?: string;
}

const RING_SIZE = 56;
const STROKE_WIDTH = 5;
const R = (RING_SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * R;

export default function AnimatedRingKpi({
  title,
  percent,
  icon,
  color = Theme.colors.primary,
  subtitle,
}: Props) {
  const progress = useRef(new Animated.Value(0)).current;
  const countUp = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(progress, {
      toValue: percent,
      duration: 900,
      delay: 100,
      useNativeDriver: false,
    }).start();
    Animated.timing(countUp, {
      toValue: percent,
      duration: 900,
      delay: 100,
      useNativeDriver: false,
    }).start();
  }, [percent]);

  const strokeDashoffset = progress.interpolate({
    inputRange: [0, 100],
    outputRange: [CIRCUMFERENCE, 0],
  });

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        <View style={[styles.iconWrapper, { backgroundColor: `${color}15` }]}>
          <MaterialCommunityIcons name={icon as any} size={20} color={color} />
        </View>
      </View>

      <View style={styles.ringRow}>
        <View style={styles.ringWrapper}>
          <Svg width={RING_SIZE} height={RING_SIZE}>
            <G rotation="-90" origin={`${RING_SIZE / 2}, ${RING_SIZE / 2}`}>
              {/* Track */}
              <Circle
                cx={RING_SIZE / 2}
                cy={RING_SIZE / 2}
                r={R}
                stroke={`${color}20`}
                strokeWidth={STROKE_WIDTH}
                fill="none"
              />
              {/* Animated fill arc */}
              <AnimatedCircle
                cx={RING_SIZE / 2}
                cy={RING_SIZE / 2}
                r={R}
                stroke={color}
                strokeWidth={STROKE_WIDTH}
                fill="none"
                strokeDasharray={`${CIRCUMFERENCE}`}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
              />
            </G>
          </Svg>
          {/* Count-up label centred over ring */}
          <View style={styles.ringCenter}>
            <AnimatedText countUp={countUp} color={color} />
          </View>
        </View>
      </View>

      {subtitle && (
        <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>
      )}
    </View>
  );
}

function AnimatedText({ countUp, color }: { countUp: Animated.Value; color: string }) {
  const [display, setDisplay] = React.useState('0%');
  useEffect(() => {
    const id = countUp.addListener(({ value }) => {
      setDisplay(`${Math.round(value)}%`);
    });
    return () => countUp.removeListener(id);
  }, []);
  return <Text style={[styles.ringLabel, { color }]}>{display}</Text>;
}

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
    marginBottom: 10,
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
  ringRow: {
    alignItems: 'flex-start',
  },
  ringWrapper: {
    width: RING_SIZE,
    height: RING_SIZE,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ringCenter: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  ringLabel: {
    fontSize: 11,
    fontWeight: 'bold',
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 10,
    color: Theme.colors.placeholder,
    marginTop: 8,
  },
});
