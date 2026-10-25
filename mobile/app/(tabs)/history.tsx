import { HeartRateCharts } from "@/components/HeartRateCharts";
import { Vo2MaxTrends } from "@/components/Vo2MaxTrends";
import { HealthTrendDetails } from "@/components/HealthTrendDetails";
import { Icon } from "@/components/Icon";
import { ExperimentalNotice } from "@/components/ExperimentalNotice";
import { AppHeader } from "@/components/AppHeader";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import type { TrendRange } from "@/api/types";
import { useAlertHistory, useTrends, useMeasurements } from "@/api/hooks";
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
  const [metric, setMetric] = useState("hr");
  const trends = useTrends(range);
  const history = useAlertHistory();
  const measurements = useMeasurements();
  const series = trends.data?.series ?? [];
  const isLoading = trends.isLoading && !trends.data;
  const isEmpty = !isLoading && !trends.isError && series.every((s) => s.points.length === 0);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <AppHeader title="History" />
      <ScrollView contentContainerStyle={styles.content}>


        <RangeToggle value={range} onChange={setRange} />
        <View style={styles.filters}>{[["all", "All metrics"], ["hr", "Heart rate"], ["hrv", "HRV"], ["spo2", "SpO₂"], ["vo2max", "VO₂ max"]].map(([key, label]) => <Pressable key={key} onPress={() => setMetric(key)} accessibilityRole="button" accessibilityState={{ selected: metric === key }} style={[styles.filter, metric === key && { backgroundColor: theme.colors.accent }]}><Text style={[styles.filterText, metric === key && { color: theme.colors.onAccent }]}>{label}</Text></Pressable>)}</View>

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
          series.filter((s) => metric === "all" || s.metric === metric).filter(s => s.metric !== "vo2max").map((s) => <TrendChart key={s.metric} series={s} />)
        )}

        {measurements.data && (metric === "hr" || metric === "all") && <HeartRateCharts readings={measurements.data} />}
        {measurements.data && (metric === "vo2max" || metric === "all") && <Vo2MaxTrends readings={measurements.data} />}
        {measurements.data && metric !== "vo2max" && <View style={styles.card}><HealthTrendDetails readings={measurements.data} metric={metric === "all" ? "hr" : metric as "hr" | "hrv" | "spo2"} /></View>}
        <View style={styles.eventsTitle}><Icon name="clock" size={18} /><Text style={styles.eventsText}>Logged telemetry events</Text></View>
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
        <ExperimentalNotice />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  filters: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  filter: { backgroundColor: theme.colors.surfaceAlt, borderRadius: 20, paddingHorizontal: 10, paddingVertical: 9 },
  filterText: { fontFamily: theme.type.mono, color: theme.colors.textSecondary, fontSize: 11 },
  eventsTitle: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 10 },
  eventsText: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 18 },
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), paddingTop: 4, paddingBottom: 28, gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: theme.font.h1, fontWeight: "700" },
  sectionLabel: {
    color: theme.colors.textSecondary,
    fontFamily: theme.type.mono, fontSize: theme.font.caption,
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
  muted: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: theme.font.body, textAlign: "center" },
  errorTitle: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: theme.font.h2, fontWeight: "700" },
  retry: { marginTop: theme.spacing(2), backgroundColor: theme.colors.accent, borderRadius: theme.radius.sm, paddingVertical: theme.spacing(2), paddingHorizontal: theme.spacing(5) },
  retryText: { color: theme.colors.onAccent, fontWeight: "700", fontFamily: theme.type.body, fontSize: theme.font.body },
});
