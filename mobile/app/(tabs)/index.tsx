import { HeartRateCharts } from "@/components/HeartRateCharts";
import { Vo2MaxTrends } from "@/components/Vo2MaxTrends";
import { useState } from "react";
import { router } from "expo-router";
import { DailySummaryCard } from "@/components/DailySummaryCard";
import { Icon } from "@/components/Icon";
import { ExperimentalNotice } from "@/components/ExperimentalNotice";
import { AppHeader } from "@/components/AppHeader";
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
  latestForMetric,
  readingsInWindow,
  formatSampleTime,
} from "@/utils/metrics";
import { theme } from "@/theme";

/**
 * Dashboard (Task 14, Req 1).
 *
 * Shows current HR/HRV/SpO2/rhythm, sleep, a monitoring-status
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
  const [windowHours, setWindowHours] = useState<number | null>(24);
  const selectedReadings = readingsInWindow(readings ?? [], windowHours);
  const windowLabel = windowHours === 24 ? "Last 24 hours" : windowHours === 168 ? "Last 7 days" : "All data";
  const latestTimestamp = readings?.reduce((last, r) => r.timestamp > last ? r.timestamp : last, "");
  const alertState: AlertState = insights.data?.state ?? "normal";
  const monitoringTitle = insights.data?.title;
  const simRunning = scenario.data?.status === "running";

  const isLoading = measurements.isLoading && !readings;
  const hasError = measurements.isError;
  const isEmpty = !isLoading && !hasError && (!readings || readings.length === 0);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <AppHeader title="Dashboard" />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.intro}><Text style={styles.eyebrow}>YOUR DAILY PULSE</Text><Text accessibilityRole="header" style={styles.h1}>Small signals.
A clearer picture.</Text><Text style={styles.introText}>Your latest readings, with room to explore the patterns.</Text></View>

        {isLoading ? (
          <View style={styles.centerCard}>
            <ActivityIndicator color={theme.colors.accent} />
            <Text style={styles.muted}>Loading measurements…</Text>
          </View>
        ) : hasError ? (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>Readings unavailable</Text>
            <Text style={styles.muted}>
              Your readings couldn’t load. Try again in a moment.
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
              Explore a demo scenario to see how your readings change.
            </Text>
            <Pressable accessibilityRole="button" onPress={() => router.push("/(tabs)/simulator")} style={styles.retry}><Text style={styles.retryText}>Explore demo scenarios</Text></Pressable>
          </View>
        ) : (
          <>
            <View style={styles.sectionRow}><Text style={styles.sectionLabel}>Health measurements</Text><WearableBadge connected={!!scenario.data} simulating={simRunning} /></View>
            <View style={styles.windows}>{([[24, "24 hours"], [168, "7 days"], [null, "All data"]] as const).map(([hours, label]) => <Pressable key={label} accessibilityRole="button" accessibilityState={{ selected: windowHours === hours }} onPress={() => setWindowHours(hours)} style={[styles.window, windowHours === hours && { backgroundColor: theme.colors.accent }]}><Text style={[styles.windowText, windowHours === hours && { color: theme.colors.onAccent }]}>{label}</Text></Pressable>)}</View>
            <Text style={styles.dataTime}>Simulation through {formatSampleTime(latestTimestamp)}. Windows follow the simulation clock.</Text>
            <View style={styles.grid}>
              {PRIMARY_METRICS.map((metric) => (
                <MetricCard
                  key={metric}
                  metric={metric}
                  reading={latestForMetric(readings, metric)}
                  readings={selectedReadings}
                  historyReadings={readings}
                  windowLabel={windowLabel}
                />
              ))}
            </View>

            <View style={styles.sectionIntro}><Text style={styles.eyebrow}>THE BIGGER PICTURE</Text><Text accessibilityRole="header" style={styles.sectionTitle}>Your heart over time</Text><Text style={styles.introText}>Compare today’s heart rate with your daily range.</Text></View>
            <HeartRateCharts readings={readings ?? []} compact />
            <Vo2MaxTrends readings={readings ?? []} />
            <Text accessibilityRole="header" style={styles.sectionTitle}>Rest & recovery</Text>
            <DailySummaryCard metric="sleep" reading={latestForMetric(readings, "sleep")} />
          </>
        )}
        {!isEmpty && !hasError && !isLoading && insights.data && <MonitoringStatusCard state={alertState} title={monitoringTitle} />}
        <Pressable style={({ pressed }) => [styles.scenarioCard, pressed && { backgroundColor: theme.colors.accentSoft }]} onPress={() => router.push("/(tabs)/simulator")} accessibilityRole="button" accessibilityLabel="Open simulator">
          <View style={styles.scenarioIcon}><Icon name="sliders" /></View>
          <View style={{ flex: 1 }}><Text style={styles.scenarioTitle}>Scenario: {scenario.data?.scenario === "B" ? "Gradual Deviation" : scenario.data?.scenario === "C" ? "Rhythm Irregularity" : "Normal Baseline"}</Text><Text style={styles.scenarioSub}>Explore synthetic monitoring patterns</Text></View>
          <Text style={styles.tune}>Explore</Text>
        </Pressable>
        <ExperimentalNotice />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  intro: { gap: 10, paddingTop: 16, paddingBottom: 16 },
  eyebrow: { fontFamily: theme.type.mono, fontSize: 11, letterSpacing: 1.4, color: theme.colors.accent },
  sectionIntro: { gap: 8, marginTop: 20 },
  sectionTitle: { fontFamily: theme.type.heading, fontSize: 24, color: theme.colors.textPrimary, marginTop: 8 },
  introText: { fontFamily: theme.type.body, color: theme.colors.textSecondary, fontSize: 14, lineHeight: 22 },
  windows: { flexDirection: "row", backgroundColor: theme.colors.surfaceAlt, borderRadius: 14, padding: 4, gap: 4 },
  window: { flex: 1, alignItems: "center", paddingVertical: 12, borderRadius: 10 },
  windowText: { fontFamily: theme.type.body, color: theme.colors.textPrimary, fontSize: 13 },
  dataTime: { fontFamily: theme.type.body, color: theme.colors.textSecondary, fontSize: 12, lineHeight: 19 },
  sectionRow: { flexDirection: "row", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" },
  scenarioCard: { backgroundColor: theme.colors.surface, borderRadius: 15, padding: 13, gap: 10, flexDirection: "row", alignItems: "center" },
  scenarioIcon: { backgroundColor: theme.colors.surfaceAlt, padding: 8, borderRadius: 9 },
  scenarioTitle: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 14 },
  scenarioSub: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 11, marginTop: 4 },
  tune: { color: theme.colors.onAccent, backgroundColor: theme.colors.accent, fontFamily: theme.type.mono, fontSize: 10, padding: 9, borderRadius: 8, overflow: "hidden" },
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), paddingTop: 4, paddingBottom: 28, gap: theme.spacing(3) },
  header: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  headerText: { flex: 1 },
  h1: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 34, lineHeight: 41, letterSpacing: -1 },
  sub: { color: theme.colors.textSecondary, fontFamily: theme.type.heading, fontSize: theme.font.h2 },
  sectionLabel: {
    color: theme.colors.textSecondary,
    fontFamily: theme.type.heading, fontSize: 17,
    marginTop: theme.spacing(1),
  },
  grid: { gap: 14 },
  centerCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(6),
    alignItems: "center",
    gap: theme.spacing(2),
  },
  muted: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: theme.font.body, textAlign: "center" },
  errorTitle: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: theme.font.h2, fontWeight: "700" },
  retry: {
    marginTop: theme.spacing(2),
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.sm,
    paddingVertical: theme.spacing(2),
    paddingHorizontal: theme.spacing(5),
  },
  retryText: { color: theme.colors.onAccent, fontWeight: "700", fontFamily: theme.type.body, fontSize: theme.font.body },
});
