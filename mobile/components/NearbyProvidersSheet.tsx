import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";

import { useProviders } from "@/api/hooks";
import type { ProviderSuggestion } from "@/api/types";
import { ProviderSuggestionCard } from "@/components/ProviderSuggestionCard";
import { theme } from "@/theme";

/**
 * Sheet of ranked nearby providers (Task 24, Owner: maiabrunne).
 *
 * Shown automatically on a `trend_review`/`attention` alert WHEN suggestions are
 * enabled (Req 10.5); may also be opened manually when disabled (Req 10.6). The
 * caller controls visibility — this component just renders the ranked list for a
 * resolved location, plus an approximate-location indicator (Req 10.8).
 */
export function NearbyProvidersSheet({
  lat,
  lon,
  emergency = false,
  approximateLocation = false,
}: {
  lat: number | null;
  lon: number | null;
  emergency?: boolean;
  approximateLocation?: boolean;
}) {
  const { data, isLoading, isError, error } = useProviders(
    { lat: lat ?? 0, lon: lon ?? 0, emergency },
    { enabled: lat != null && lon != null },
  );

  if (lat == null || lon == null) {
    return (
      <View style={styles.container}>
        <Text style={styles.empty}>
          Location unavailable. Set a default location in Settings to see nearby providers.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Nearby providers</Text>
        <Text style={styles.synthetic}>Synthetic directory — for demonstration</Text>
      </View>

      {approximateLocation ? (
        <Text style={styles.approx} accessibilityRole="alert">
          Using an approximate (default) location — distances are estimates.
        </Text>
      ) : null}

      {isLoading ? (
        <ActivityIndicator color={theme.colors.accent} style={styles.loader} />
      ) : isError ? (
        <Text style={styles.error}>
          Could not load providers: {(error as Error)?.message ?? "unknown error"}
        </Text>
      ) : !data || data.length === 0 ? (
        <Text style={styles.empty}>No providers found in the directory.</Text>
      ) : (
        <FlatList
          data={data}
          keyExtractor={(s: ProviderSuggestion) => String(s.provider.id)}
          renderItem={({ item }) => <ProviderSuggestionCard suggestion={item} />}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: theme.spacing(2) },
  header: { gap: 2 },
  title: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700" },
  synthetic: { color: theme.colors.experimental, fontSize: theme.font.caption, fontWeight: "600" },
  approx: { color: theme.colors.warn, fontSize: theme.font.caption },
  loader: { marginVertical: theme.spacing(4) },
  error: { color: theme.colors.danger, fontSize: theme.font.body },
  empty: { color: theme.colors.textSecondary, fontSize: theme.font.body },
  list: { gap: theme.spacing(2) },
  sep: { height: theme.spacing(2) },
});
