import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/theme";

interface WearableBadgeProps {
  /** Whether a (simulated) wearable source is connected. */
  connected: boolean;
  /** Whether the simulator is actively streaming. */
  simulating: boolean;
}

/**
 * Wearable connection status badge (Req 1.4). In the MVP the "device" is the
 * simulator, so this reflects the simulated source and whether it is live.
 */
export function WearableBadge({ connected, simulating }: WearableBadgeProps) {
  const color = connected ? (simulating ? theme.colors.accentGreen : theme.colors.accent) : theme.colors.textSecondary;
  const label = !connected ? "No source" : simulating ? "Live (simulated)" : "Connected (simulated)";

  return (
    <View style={[styles.badge, { borderColor: color }]} accessibilityLabel={`Wearable: ${label}`}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing(2),
    borderWidth: 1,
    borderRadius: theme.radius.lg,
    paddingVertical: theme.spacing(1),
    paddingHorizontal: theme.spacing(3),
  },
  dot: { width: 8, height: 8, borderRadius: 4 },
  text: { fontSize: theme.font.caption, fontWeight: "600" },
});
