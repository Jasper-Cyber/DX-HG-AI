import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import type { AlertState } from "@/api/types";
import { useInsights, useMeasurements, useScenario } from "@/api/hooks";
import { MetricCard } from "@/components/MetricCard";
import { MonitoringStatusCard } from "@/components/MonitoringStatusCard";
import { SimulatedDataRibbon } from "@/components/SimulatedDataRibbon";
import { WearableBadge } from "@/components/WearableBadge";
import {
  PRIMARY_METRICS,
  SECONDARY_METRICS,
  latestForMetric,
  miniSeriesForMetric,
} from "@/utils/metrics";
import { theme } from "@/theme";

/**
 * Dashboard (Task 14, Req 1).
 *
 * Shows current HR/HRV/SpO2/rhythm, daily activity/sleep, a monitoring-status
 * card (from the current alert state) and a wearable-connection badge (derived
 * from the simulator session), with mini trend charts per metric. Data polls
 * live while the simulator runs. All values are labeled simulated via the
 * always-visible ribbon.
 */
export default function DashboardScreen() {
  const measurements = useMeasurements();
  const insights = useInsights();
  const scenario = useScenario();

  const readings = measurements.data;
  const alertState: AlertState = insights.data?.state ?? "normal";
  const monitoringTitle = insights.data?.title;
  const simRunning = scenario.data?.status === "running";

  const isLoading = measurements.isLoading && !readings;
  const hasError = measurements.isError;
  const isEmpty = !isLoading && !hasError && (!readings || readings.length === 0);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <View style={styles.headerText}>
            <Text style={styles.h1}>HeartGuardian AI</Text>
            <Text style={styles.sub}>Dashboard</Text>
          </View>
          <WearableBadge connected={!!scenario.data} simulating={simRunning} />
        </View>

        <MonitoringStatusCard state={alertState} title={monitoringTitle} />

        {isLoading ? (
          <View style={styles.centerCard}>
            <ActivityIndicator color={theme.colors.accent} />
            <Text style={styles.muted}>Loading measurements…</Text>
          </View>
        ) : hasError ? (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>Can’t reach the backend</Text>
            <Text style={styles.muted}>
              Make sure the API is running, then retry.
            </Text>
            <Pressable
              style={styles.retry}
              onPress={() => measurements.refetch()}
              accessibilityRole="button"
            >
              <Text style={styles.retryText}>Retry</Text>
            </Pressable>
          </View>
        ) : isEmpty ? (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>No data yet</Text>
            <Text style={styles.muted}>
              Start the simulator to generate synthetic readings.
            </Text>
          </View>
        ) : (
          <>
            <Text style={styles.sectionLabel}>Current metrics</Text>
            <View style={styles.grid}>
              {PRIMARY_METRICS.map((metric) => (
                <MetricCard
                  key={metric}
                  metric={metric}
                  reading={latestForMetric(readings, metric)}
                  series={miniSeriesForMetric(readings, metric)}
                />
              ))}
            </View>

            <Text style={styles.sectionLabel}>Today</Text>
            <View style={styles.grid}>
              {SECONDARY_METRICS.map((metric) => (
                <MetricCard
                  key={metric}
                  metric={metric}
                  reading={latestForMetric(readings, metric)}
                  series={miniSeriesForMetric(readings, metric)}
                />
              ))}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  header: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  headerText: { flex: 1 },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  sub: { color: theme.colors.textSecondary, fontSize: theme.font.h2 },
  sectionLabel: {
    color: theme.colors.textSecondary,
    fontSize: theme.font.caption,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: theme.spacing(1),
  },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: theme.spacing(3) },
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
  retry: {
    marginTop: theme.spacing(2),
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.sm,
    paddingVertical: theme.spacing(2),
    paddingHorizontal: theme.spacing(5),
  },
  retryText: { color: theme.colors.bg, fontWeight: "700", fontSize: theme.font.body },
});
