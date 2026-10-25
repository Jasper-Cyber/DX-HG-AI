import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/theme";

/**
 * Always-visible banner marking that the data shown is synthetic/experimental.
 * Required on data surfaces (Req 1.5, 8.5).
 */
export function SimulatedDataRibbon() {
  return (
    <View style={styles.ribbon} accessibilityRole="alert">
      <Text style={styles.text}>SIMULATED DATA — experimental prototype, not medical advice</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  ribbon: {
    backgroundColor: theme.colors.surfaceAlt,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.experimental,
    paddingVertical: theme.spacing(2),
    paddingHorizontal: theme.spacing(3),
  },
  text: {
    color: theme.colors.experimental,
    fontSize: theme.font.caption,
    fontWeight: "600",
    textAlign: "center",
  },
});
