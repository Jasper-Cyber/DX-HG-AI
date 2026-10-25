import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useInsights } from "@/api/hooks";
import { AlertBanner } from "@/components/AlertBanner";
import { EmergencyGuidanceCard } from "@/components/EmergencyGuidanceCard";
import { ExperimentalNotice } from "@/components/ExperimentalNotice";
import { SimulatedDataRibbon } from "@/components/SimulatedDataRibbon";
import { alertStateMeta } from "@/utils/alerts";
import { theme } from "@/theme";

/**
 * Insights / Alerts (Task 15, Req 4).
 *
 * Shows the current alert state banner, the supporting-data explanation and
 * next steps, an always-visible emergency guidance card, and the concise
 * experimental/not-liable notice. Non-diagnostic wording throughout.
 */
export default function InsightsScreen() {
  const insights = useInsights();
  const alert = insights.data;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.h1}>Insights</Text>

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
            <AlertBanner state={alert.state} title={alert.title || alertStateMeta(alert.state).defaultTitle} />

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>What the data shows</Text>
              <Text style={styles.body}>{alert.explanation}</Text>
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Suggested next steps</Text>
              <Text style={styles.body}>{alert.nextSteps}</Text>
            </View>

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
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(4),
    gap: theme.spacing(2),
  },
  sectionTitle: { color: theme.colors.textSecondary, fontSize: theme.font.caption, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  body: { color: theme.colors.textPrimary, fontSize: theme.font.body, lineHeight: 22 },
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
