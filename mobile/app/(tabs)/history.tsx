import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import type { TrendRange } from "@/api/types";
import { useAlertHistory, useTrends } from "@/api/hooks";
import { PastAlertsList } from "@/components/PastAlertsList";
import { RangeToggle } from "@/components/RangeToggle";
import { SimulatedDataRibbon } from "@/components/SimulatedDataRibbon";
import { TrendChart } from "@/components/TrendChart";
import { theme } from "@/theme";

/**
 * History (Task 16, Req 5).
 *
 * Daily/weekly/monthly toggle driving per-metric trend charts with a baseline
 * overlay and anomaly markers, plus a past-alerts list. Explicit empty states
 * when a range has no data.
 */
export default function HistoryScreen() {
  const [range, setRange] = useState<TrendRange>("daily");
  const trends = useTrends(range);
  const history = useAlertHistory();
  const series = trends.data?.series ?? [];
  const isLoading = trends.isLoading && !trends.data;
  const isEmpty = !isLoading && !trends.isError && series.every((s) => s.points.length === 0);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.h1}>History</Text>

        <RangeToggle value={range} onChange={setRange} />

        {isLoading ? (
          <View style={styles.centerCard}>
            <ActivityIndicator color={theme.colors.accent} />
            <Text style={styles.muted}>Loading {range} trends…</Text>
          </View>
        ) : trends.isError ? (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>Can’t reach the backend</Text>
            <Text style={styles.muted}>Make sure the API is running, then retry.</Text>
            <Pressable style={styles.retry} onPress={() => trends.refetch()} accessibilityRole="button">
              <Text style={styles.retryText}>Retry</Text>
            </Pressable>
          </View>
        ) : isEmpty ? (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>No data for this range</Text>
            <Text style={styles.muted}>Try another range, or run the simulator to generate history.</Text>
          </View>
        ) : (
          series.map((s) => <TrendChart key={s.metric} series={s} />)
        )}

        <Text style={styles.sectionLabel}>Past alerts</Text>
        <View style={styles.card}>
          {history.isLoading ? (
            <ActivityIndicator color={theme.colors.accent} />
          ) : history.isError ? (
            <>
              <Text style={styles.errorTitle}>Couldn’t load alert history</Text>
              <Pressable style={styles.retry} onPress={() => history.refetch()} accessibilityRole="button">
                <Text style={styles.retryText}>Retry</Text>
              </Pressable>
            </>
          ) : <PastAlertsList alerts={history.data ?? []} />}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  sectionLabel: {
    color: theme.colors.textSecondary,
    fontSize: theme.font.caption,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: theme.spacing(1),
  },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(4),
  },
  centerCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(6),
    alignItems: "center",
    gap: theme.spacing(2),
  },
  muted: { color: theme.colors.textSecondary, fontSize: theme.font.body, textAlign: "center" },
  errorTitle: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700" },
  retry: { marginTop: theme.spacing(2), backgroundColor: theme.colors.accent, borderRadius: theme.radius.sm, paddingVertical: theme.spacing(2), paddingHorizontal: theme.spacing(5) },
  retryText: { color: theme.colors.bg, fontWeight: "700", fontSize: theme.font.body },
});
