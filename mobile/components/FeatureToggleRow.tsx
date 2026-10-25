import { StyleSheet, Switch, Text, View } from "react-native";

import { theme } from "@/theme";

interface FeatureToggleRowProps {
  label: string;
  description?: string;
  value: boolean;
  onValueChange: (next: boolean) => void;
  disabled?: boolean;
}

/** A labeled on/off row for a feature flag (Req 10.1, 11.1). */
export function FeatureToggleRow({
  label,
  description,
  value,
  onValueChange,
  disabled,
}: FeatureToggleRowProps) {
  return (
    <View style={styles.row}>
      <View style={styles.text}>
        <Text style={styles.label}>{label}</Text>
        {description ? <Text style={styles.desc}>{description}</Text> : null}
      </View>
      <Switch
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
        trackColor={{ false: theme.colors.controlBorder, true: theme.colors.accent }}
        thumbColor={theme.colors.onAccent}
        accessibilityLabel={label}
        accessibilityState={{ checked: value, disabled: !!disabled }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: theme.spacing(3),
    paddingVertical: theme.spacing(2),
  },
  text: { flex: 1 },
  label: { color: theme.colors.textPrimary, fontFamily: theme.type.body, fontSize: theme.font.body, fontWeight: "600" },
  desc: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: theme.font.caption, marginTop: theme.spacing(1) },
});
