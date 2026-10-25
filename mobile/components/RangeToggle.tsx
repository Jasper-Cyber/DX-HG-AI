import { Pressable, StyleSheet, Text, View } from "react-native";

import type { TrendRange } from "@/api/types";
import { theme } from "@/theme";

interface RangeToggleProps {
  value: TrendRange;
  onChange: (range: TrendRange) => void;
}

const RANGES: { key: TrendRange; label: string }[] = [
  { key: "daily", label: "Daily" },
  { key: "weekly", label: "Weekly" },
  { key: "monthly", label: "Monthly" },
];

/** Segmented daily/weekly/monthly selector for the History screen (Req 5.1). */
export function RangeToggle({ value, onChange }: RangeToggleProps) {
  return (
    <View style={styles.row} accessibilityRole="tablist">
      {RANGES.map((r) => {
        const active = r.key === value;
        return (
          <Pressable
            key={r.key}
            style={[styles.segment, active && styles.segmentActive]}
            onPress={() => onChange(r.key)}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
          >
            <Text style={[styles.label, active && styles.labelActive]}>{r.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(1),
    gap: theme.spacing(1),
  },
  segment: { flex: 1, paddingVertical: theme.spacing(2), borderRadius: theme.radius.sm, alignItems: "center" },
  segmentActive: { backgroundColor: theme.colors.accent },
  label: { color: theme.colors.textSecondary, fontSize: theme.font.body, fontWeight: "600" },
  labelActive: { color: theme.colors.bg, fontWeight: "700" },
});
