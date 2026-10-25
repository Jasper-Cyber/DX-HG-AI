import { StyleSheet, Text, View } from "react-native";

import type { DispatchChannel } from "@/api/types";
import { theme } from "@/theme";

/**
 * Badge marking whether a dispatch is simulated or real (Task 25, Owner: maiabrunne).
 * Makes the human-in-the-loop, simulated-by-default behavior explicit (Req 11.6).
 */
export function SimulatedDispatchBadge({ channel }: { channel: DispatchChannel }) {
  const simulated = channel === "simulated";
  const color = simulated ? theme.colors.experimental : theme.colors.danger;
  const label = simulated ? "SIMULATED" : "REAL";
  return (
    <View style={[styles.badge, { borderColor: color }]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { borderWidth: 1, borderRadius: theme.radius.sm, paddingHorizontal: theme.spacing(2), paddingVertical: 2, alignSelf: "flex-start" },
  text: { fontSize: theme.font.caption, fontWeight: "700", letterSpacing: 0.5 },
});
