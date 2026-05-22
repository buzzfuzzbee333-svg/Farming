import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
  TextStyle,
  StyleProp,
} from "react-native";
import { colors, mono, radius, statusStyle } from "../lib/theme";

export function Card({
  children,
  style,
  testID,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}) {
  return (
    <View style={[styles.card, style]} testID={testID}>
      {children}
    </View>
  );
}

export function Badge({
  status,
  label,
  testID,
}: {
  status: string;
  label?: string;
  testID?: string;
}) {
  const s = statusStyle(status);
  return (
    <View
      testID={testID}
      style={[
        styles.badge,
        { backgroundColor: s.bg, borderColor: s.border },
      ]}
    >
      <Text style={[styles.badgeText, { color: s.fg }]}>
        {(label ?? status).toUpperCase()}
      </Text>
    </View>
  );
}

export function PrimaryButton({
  label,
  onPress,
  testID,
  disabled,
  style,
}: {
  label: string;
  onPress: () => void;
  testID?: string;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.8}
      style={[
        styles.btnPrimary,
        disabled && { opacity: 0.4 },
        style,
      ]}
    >
      <Text style={styles.btnPrimaryText}>{label}</Text>
    </TouchableOpacity>
  );
}

export function SecondaryButton({
  label,
  onPress,
  testID,
  style,
}: {
  label: string;
  onPress: () => void;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      activeOpacity={0.7}
      style={[styles.btnSecondary, style]}
    >
      <Text style={styles.btnSecondaryText}>{label}</Text>
    </TouchableOpacity>
  );
}

export function StatBlock({
  label,
  value,
  accent,
  style,
  testID,
}: {
  label: string;
  value: string;
  accent?: boolean;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}) {
  return (
    <View style={[styles.statBlock, style]} testID={testID}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text
        style={[styles.statValue, accent && { color: colors.accent }]}
        numberOfLines={1}
        adjustsFontSizeToFit
      >
        {value}
      </Text>
    </View>
  );
}

export function SectionLabel({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<TextStyle>;
}) {
  return <Text style={[styles.sectionLabel, style]}>{children}</Text>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: 16,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.sm,
    borderWidth: 1,
    alignSelf: "flex-start",
  },
  badgeText: {
    fontFamily: mono,
    fontSize: 10,
    letterSpacing: 1.5,
    fontWeight: "700",
  },
  btnPrimary: {
    backgroundColor: colors.accent,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  btnPrimaryText: {
    color: "#000",
    fontFamily: mono,
    fontWeight: "800",
    fontSize: 13,
    letterSpacing: 1.5,
    textTransform: "uppercase",
  },
  btnSecondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  btnSecondaryText: {
    color: colors.text,
    fontFamily: mono,
    fontSize: 13,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  statBlock: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    borderRadius: radius.sm,
  },
  statLabel: {
    fontFamily: mono,
    fontSize: 9,
    color: colors.textTertiary,
    letterSpacing: 2,
    textTransform: "uppercase",
    marginBottom: 6,
  },
  statValue: {
    fontFamily: mono,
    fontSize: 22,
    color: colors.text,
    fontWeight: "700",
    letterSpacing: -0.5,
  },
  sectionLabel: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 10,
    letterSpacing: 2,
    textTransform: "uppercase",
    marginBottom: 8,
  },
});
