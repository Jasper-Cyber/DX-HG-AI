import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/theme";

/**
 * Concise "experimental / not medical advice / not liable" notice.
 *
 * Appears on alert and dispatch surfaces (Req 4.5, 12.6). Shared constant copy
 * so every surface shows the same wording.
 */
export const EXPERIMENTAL_NOTICE =
  "Experimental prototype — not medical advice. Warnings may be false or missed; " +
  "acting on them is your decision. For emergencies, contact local emergency services.";

export function ExperimentalNotice() {
  return (
    <View style={styles.wrap} accessibilityRole="alert">
      <Text style={styles.text}>{EXPERIMENTAL_NOTICE}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderColor: theme.colors.inset,
    borderRadius: theme.radius.sm,
    backgroundColor: theme.colors.inset,
    padding: theme.spacing(3),
  },
  text: { color: theme.colors.experimental, fontFamily: theme.type.mono, fontSize: theme.font.caption, lineHeight: 18 },
});
