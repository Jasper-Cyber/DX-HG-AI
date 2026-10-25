import { Vo2MaxTrends } from "@/components/Vo2MaxTrends";
import { TrendComparisonList } from "@/components/TrendComparisonList";
import { useState } from "react";
import { Icon } from "@/components/Icon";
import { useMeasurements } from "@/api/hooks";
import { latestForMetric, formatMetricValue, hasUsableValue } from "@/utils/metrics";
import { AppHeader } from "@/components/AppHeader";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useInsights } from "@/api/hooks";
import { AlertBanner } from "@/components/AlertBanner";
import { EmergencyGuidanceCard } from "@/components/EmergencyGuidanceCard";
import { ExperimentalNotice } from "@/components/ExperimentalNotice";
import { SimulatedDataRibbon } from "@/components/SimulatedDataRibbon";
import { alertStateMeta } from "@/utils/alerts";
import { theme, metricPalette } from "@/theme";

/**
 * Insights / Alerts (Task 15, Req 4).
 *
 * Shows the current alert state banner, the supporting-data explanation and
 * next steps, an always-visible emergency guidance card, and the concise
 * experimental/not-liable notice. Non-diagnostic wording throughout.
 */
export default function InsightsScreen() {
  const insights = useInsights();
  const measurements = useMeasurements();
  const [expanded, setExpanded] = useState(false);
  const alert = insights.data;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <AppHeader title="Insights" />
      <ScrollView contentContainerStyle={styles.content}>


        {insights.isLoading && !alert ? (
          <View style={styles.centerCard}>
            <ActivityIndicator color={theme.colors.accent} />
            <Text style={styles.muted}>Loading insights…</Text>
          </View>
        ) : insights.isError ? (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>Can’t reach the backend</Text>
            <Text style={styles.muted}>Make sure the API is running, then retry.</Text>
            <Pressable style={styles.retry} onPress={() => insights.refetch()} accessibilityRole="button">
              <Text style={styles.retryText}>Retry</Text>
            </Pressable>
          </View>
        ) : alert ? (
          <>
            <View style={styles.states}>{(["normal", "trend_review", "attention"] as const).map((state, i) => <View key={state} style={[styles.state, state === alert.state && { backgroundColor: theme.colors.surfaceAlt }]}><View style={{ width: 4, height: 4, borderRadius: 4, backgroundColor: [theme.colors.accent, theme.colors.warn, theme.colors.danger][i] }} /><Text style={styles.stateText}>{["Normal", "Trend", "Alert"][i]}</Text></View>)}</View>
            {measurements.data && <TrendComparisonList readings={measurements.data} />}
            {measurements.data && <Vo2MaxTrends readings={measurements.data} />}
            <AlertBanner state={alert.state} title={alert.title || alertStateMeta(alert.state).defaultTitle} />

            <View style={styles.card}>
              <View style={styles.cardHeading}><Icon name="sparkles" size={18} /><Text style={styles.cardTitle}>What the data shows</Text><Text style={styles.tag}>ANALYSIS</Text></View>
              <Text style={styles.body}>{alert.explanation}</Text>
              <View style={styles.evidence}>{(["hr", "hrv", "spo2"] as const).map((metric, i) => { const reading = latestForMetric(measurements.data, metric); return <View key={metric} style={[styles.evidenceCell, { backgroundColor: metricPalette[metric].soft }]}><Text style={styles.evidenceLabel}>{["HEART RATE", "HRV RMSSD", "SpO₂"][i]}</Text><Text style={[styles.evidenceValue, { color: metricPalette[metric].ink }]}>{formatMetricValue(hasUsableValue(reading) ? reading!.value : null, metric)} <Text style={styles.evidenceLabel}>{["bpm", "ms", "%"][i]}</Text></Text><Text style={[styles.evidenceNote, { color: metricPalette[metric].ink }]}>Latest sample</Text></View>; })}</View>
            </View>

            <View style={styles.card}>
              <View style={styles.cardHeading}><Icon name="shield" size={18} /><Text style={styles.cardTitle}>Suggested next steps</Text></View>
              <Text style={styles.body}>{alert.nextSteps}</Text><Text style={styles.evidenceNote}>Non-diagnostic suggestions based on synthetic telemetry.</Text>
            </View>

            <Pressable style={styles.card} onPress={() => setExpanded(!expanded)} accessibilityRole="button" accessibilityState={{ expanded }}>
              <View style={styles.cardHeading}><Icon name="sliders" size={18} /><Text style={styles.cardTitle}>How alerts are classified</Text><Icon name="chevron" size={15} /></View>
              <Text style={styles.evidenceLabel}>Explore the monitoring states</Text>
              {expanded && <Text style={styles.body}>Normal means no escalating findings are currently stored. Trend review surfaces sustained deviations; Attention marks findings for further assessment. Data-quality findings do not escalate the alert by themselves. These are experimental signals, not diagnoses.</Text>}
            </Pressable>
            <EmergencyGuidanceCard guidance={alert.emergencyGuidance} />

            <ExperimentalNotice />
          </>
        ) : (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>No insights yet</Text>
            <Text style={styles.muted}>Run the simulator and analysis to generate insights.</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  states: { flexDirection: "row", backgroundColor: theme.colors.surface, padding: 5, borderRadius: 12 },
  state: { flex: 1, flexDirection: "row", gap: 6, alignItems: "center", justifyContent: "center", paddingVertical: 8, borderRadius: 8 },
  stateText: { color: theme.colors.textPrimary, fontFamily: theme.type.mono, fontSize: 11 },
  cardHeading: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardTitle: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 16, flex: 1 },
  tag: { color: theme.colors.pale, backgroundColor: theme.colors.surfaceAlt, fontFamily: theme.type.mono, fontSize: 11, padding: 5, borderRadius: 6 },
  evidence: { flexDirection: "row", gap: 6, marginTop: 8 },
  evidenceCell: { flex: 1, padding: 8, borderRadius: 8, backgroundColor: theme.colors.inset },
  evidenceLabel: { fontFamily: theme.type.mono, color: theme.colors.textSecondary, fontSize: 11 },
  evidenceValue: { fontFamily: theme.type.heading, color: theme.colors.textPrimary, fontSize: 20, marginVertical: 6 },
  evidenceNote: { fontFamily: theme.type.mono, color: theme.colors.accentGreen, fontSize: 11, lineHeight: 15, marginTop: 7 },
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), paddingTop: 4, paddingBottom: 28, gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: theme.font.h1, fontWeight: "700" },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 0,
    padding: theme.spacing(4),
    gap: theme.spacing(2),
  },
  sectionTitle: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: theme.font.caption, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  body: { color: theme.colors.textPrimary, fontFamily: theme.type.body, fontSize: theme.font.body, lineHeight: 22 },
  centerCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 0,
    padding: theme.spacing(6),
    alignItems: "center",
    gap: theme.spacing(2),
  },
  muted: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: theme.font.body, textAlign: "center" },
  errorTitle: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: theme.font.h2, fontWeight: "700" },
  retry: { marginTop: theme.spacing(2), backgroundColor: theme.colors.accent, borderRadius: theme.radius.sm, paddingVertical: theme.spacing(2), paddingHorizontal: theme.spacing(5) },
  retryText: { color: theme.colors.onAccent, fontWeight: "700", fontFamily: theme.type.body, fontSize: theme.font.body },
});
