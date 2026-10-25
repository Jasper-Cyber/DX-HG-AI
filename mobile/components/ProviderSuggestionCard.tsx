import { StyleSheet, Text, View } from "react-native";

import type { ProviderSuggestion } from "@/api/types";
import { theme } from "@/theme";

/**
 * A single nearby-provider suggestion (Task 24, Owner: maiabrunne).
 * Shows name, type/specialty, distance, a "Preferred" badge for the user's
 * preferred doctor (Req 10.9), a cardiac-capable badge, and a synthetic label (Req 10.10).
 */
export function ProviderSuggestionCard({
  suggestion,
}: {
  suggestion: ProviderSuggestion;
}) {
  const { provider, distanceKm, isPreferred } = suggestion;
  const subtitle = [provider.kind, provider.specialty].filter(Boolean).join(" · ");

  return (
    <View style={styles.card} accessibilityRole="summary">
      <View style={styles.row}>
        <Text style={styles.name} numberOfLines={1}>
          {provider.name}
        </Text>
        <Text style={styles.distance}>{distanceKm.toFixed(1)} km</Text>
      </View>

      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}

      <View style={styles.badges}>
        {isPreferred ? (
          <Badge label="Preferred" color={theme.colors.accentGreen} />
        ) : null}
        {provider.canHandleCardiacEmergency ? (
          <Badge label="Cardiac-capable" color={theme.colors.accent} />
        ) : null}
        {provider.isSynthetic ? (
          <Badge label="Synthetic" color={theme.colors.experimental} />
        ) : null}
      </View>

      {provider.phone ? <Text style={styles.phone}>{provider.phone}</Text> : null}
    </View>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <View style={[styles.badge, { borderColor: color }]}>
      <Text style={[styles.badgeText, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(3),
    gap: theme.spacing(1),
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  name: { color: theme.colors.textPrimary, fontFamily: theme.type.body, fontSize: theme.font.body, fontWeight: "700", flexShrink: 1 },
  distance: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: theme.font.body, marginLeft: theme.spacing(2) },
  subtitle: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: theme.font.caption, textTransform: "capitalize" },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: theme.spacing(1), marginTop: theme.spacing(1) },
  badge: { borderWidth: 1, borderRadius: theme.radius.sm, paddingHorizontal: theme.spacing(2), paddingVertical: 2 },
  badgeText: { fontFamily: theme.type.mono, fontSize: theme.font.caption, fontWeight: "600" },
  phone: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: theme.font.caption, marginTop: theme.spacing(1) },
});
