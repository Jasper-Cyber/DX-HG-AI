import { Pressable, StyleSheet, Text, View } from "react-native";

import type { Scenario } from "@/api/types";
import { theme } from "@/theme";

interface ScenarioPickerProps {
  value: Scenario;
  onChange: (scenario: Scenario) => void;
  disabled?: boolean;
}

export const SCENARIOS: { key: Scenario; title: string; blurb: string }[] = [
  { key: "A", title: "Normal", blurb: "Readings fluctuate within your personal baseline." },
  { key: "B", title: "Gradual Deviation", blurb: "Resting HR drifts up, HRV down, sleep declines over weeks." },
  { key: "C", title: "Rhythm Irregularity", blurb: "Intermittent irregular-rhythm pattern with correlated HR spikes." },
];

/** Scenario selector (A/B/C) for the Simulator screen (Req 2.2, 2.6). */
export function ScenarioPicker({ value, onChange, disabled }: ScenarioPickerProps) {
  return (
    <View style={styles.list} accessibilityRole="radiogroup">
      {SCENARIOS.map((s) => {
        const active = s.key === value;
        return (
          <Pressable
            key={s.key}
            style={[styles.card, active && styles.cardActive, disabled && styles.cardDisabled]}
            onPress={() => !disabled && onChange(s.key)}
            disabled={disabled}
            accessibilityRole="radio"
            accessibilityState={{ selected: active, disabled: !!disabled }}
            accessibilityLabel={`Scenario ${s.key}: ${s.title}`}
          >
            <View style={styles.header}>
              <View style={[styles.badge, active && styles.badgeActive]}>
                <Text style={[styles.badgeText, active && styles.badgeTextActive]}>{s.key}</Text>
              </View>
              <Text style={styles.title}>{s.title}</Text>
            </View>
            <Text style={styles.blurb}>{s.blurb}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: theme.spacing(3) },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(4),
    gap: theme.spacing(2),
  },
  cardActive: { borderColor: theme.colors.accent, backgroundColor: theme.colors.surfaceAlt },
  cardDisabled: { opacity: 0.5 },
  header: { flexDirection: "row", alignItems: "center", gap: theme.spacing(3) },
  badge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeActive: { backgroundColor: theme.colors.accent, borderColor: theme.colors.accent },
  badgeText: { color: theme.colors.textSecondary, fontWeight: "800" },
  badgeTextActive: { color: theme.colors.bg },
  title: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700" },
  blurb: { color: theme.colors.textSecondary, fontSize: theme.font.body, lineHeight: 20 },
});
