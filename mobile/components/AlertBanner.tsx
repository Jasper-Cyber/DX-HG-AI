import { StyleSheet, Text, View } from "react-native";

import type { AlertState } from "@/api/types";
import { alertStateMeta } from "@/utils/alerts";
import { theme } from "@/theme";

interface AlertBannerProps {
  state: AlertState;
  title: string;
}

/**
 * Prominent current-state banner for the Insights screen (Req 4.1): one of
 * Normal monitoring / Trend review recommended / Needs further assessment.
 */
export function AlertBanner({ state, title }: AlertBannerProps) {
  const meta = alertStateMeta(state);
  return (
    <View
      style={[styles.banner, { backgroundColor: meta.color }]}
      accessibilityRole="header"
      accessibilityLabel={`${meta.label}. ${title}`}
    >
      <Text style={styles.state}>{meta.label.toUpperCase()}</Text>
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    borderRadius: theme.radius.md,
    padding: theme.spacing(4),
    gap: theme.spacing(1),
  },
  // Dark text on the colored banner keeps AA contrast against the bright
  // accent/warn/danger fills.
  state: { color: theme.colors.bg, fontSize: theme.font.caption, fontWeight: "800", letterSpacing: 1 },
  title: { color: theme.colors.bg, fontSize: theme.font.h2, fontWeight: "700" },
});
