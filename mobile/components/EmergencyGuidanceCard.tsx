import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/theme";

/** Static, always-visible emergency guidance (Req 4.3) — independent of readings. */
export const DEFAULT_EMERGENCY_GUIDANCE =
  "If you have symptoms of a heart attack or stroke — such as chest pain or pressure, " +
  "trouble breathing, sudden weakness or numbness, difficulty speaking, or fainting — " +
  "call your local emergency services immediately. Do not wait for this app.";

interface EmergencyGuidanceCardProps {
  /** Optional guidance text from the backend; falls back to the default copy. */
  guidance?: string;
}

/**
 * Symptom-based emergency guidance card. Always shown on the Insights screen
 * regardless of the current alert state (Req 4.3). Non-diagnostic (Req 4.4).
 */
export function EmergencyGuidanceCard({ guidance }: EmergencyGuidanceCardProps) {
  return (
    <View style={styles.card} accessibilityRole="alert">
      <Text style={styles.heading}>Emergency guidance</Text>
      <Text style={styles.body}>{guidance ?? DEFAULT_EMERGENCY_GUIDANCE}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.danger,
    borderLeftWidth: 4,
    borderLeftColor: theme.colors.danger,
    padding: theme.spacing(4),
    gap: theme.spacing(2),
  },
  heading: { color: theme.colors.danger, fontSize: theme.font.h2, fontWeight: "700" },
  body: { color: theme.colors.textPrimary, fontSize: theme.font.body, lineHeight: 22 },
});
