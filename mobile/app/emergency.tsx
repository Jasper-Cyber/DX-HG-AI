import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  useCareProfile,
  useDispatch,
  useDispatchHistory,
  useEmergencyEvaluation,
  useSettings,
} from "@/api/hooks";
import type { EmergencyDecision } from "@/api/types";
import { DispatchHistoryList } from "@/components/DispatchHistoryList";
import { EmergencyConfirmDialog } from "@/components/EmergencyConfirmDialog";
import { SimulatedDispatchBadge } from "@/components/SimulatedDispatchBadge";
import { useUserLocation } from "@/components/useUserLocation";
import { theme } from "@/theme";

/**
 * Emergency-response flow (Task 25, Owner: maiabrunne).
 *
 * Only runs when the feature is enabled (Req 11.1). Evaluates the routing decision,
 * previews the recipient + payload, and gates dispatch behind the confirm-with-
 * countdown dialog (Req 11.5). Simulated by default with a simulated/real badge
 * (Req 11.6). Static emergency-services guidance is always shown (Req 11.8), and
 * past dispatches are listed (Req 11.7).
 *
 * Wired to the merged Task 20 backend contract: evaluate/dispatch take lat/lon +
 * findingSummary and the server re-evaluates routing on dispatch.
 */
export default function EmergencyScreen() {
  const params = useLocalSearchParams<{ findingSummary?: string }>();
  const findingSummary = params.findingSummary ?? "Experimental monitoring signal flagged for review.";

  const settings = useSettings();
  const careProfile = useCareProfile();
  const location = useUserLocation(
    careProfile.data?.defaultLat ?? undefined,
    careProfile.data?.defaultLon ?? undefined,
  );
  const evaluate = useEmergencyEvaluation();
  const dispatch = useDispatch();
  const history = useDispatchHistory();

  const decision = evaluate.data?.enabled ? evaluate.data : null;
  const [confirming, setConfirming] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const enabled = settings.data?.emergencyEnabled ?? false;
  const guidance = decision?.emergencyGuidance ?? "";
  const channel = decision?.channel ?? "simulated";

  const { mutate: evaluateDecision, reset: resetEvaluation } = evaluate;
  const retryEvaluation = () => evaluateDecision({
    lat: location.lat, lon: location.lon, findingSummary,
  });

  useEffect(() => {
    setConfirming(false);
    resetEvaluation();
    if (!enabled || !location.resolved || careProfile.isPending) return;
    evaluateDecision({ lat: location.lat, lon: location.lon, findingSummary });
  }, [enabled, location.resolved, location.lat, location.lon, careProfile.isPending,
      findingSummary, evaluateDecision, resetEvaluation]);

  const onConfirm = () => {
    // Dispatch with the SAME coordinates the decision was evaluated against, so
    // the backend re-resolves to the exact recipient that was previewed and
    // confirmed (avoids a confirm-vs-dispatch split-brain and never sends null
    // when evaluation used the profile default). Fall back to live location only
    // if the decision payload somehow lacks coordinates.
    const decidedLat = decision?.payload?.location?.lat ?? location.lat;
    const decidedLon = decision?.payload?.location?.lon ?? location.lon;
    dispatch.mutate(
      { lat: decidedLat, lon: decidedLon, findingSummary, confirmed: true },
      {
        onSuccess: (res) => {
          setLastResult(
            `Dispatch ${res.status} via ${res.channel} channel (event #${res.id ?? "?"}).`,
          );
          setConfirming(false);
          void history.refetch();
        },
        onError: (err) => {
          setLastResult((err as Error).message);
          setConfirming(false);
        },
      },
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.h1}>Emergency response</Text>
        <Text style={styles.notice}>
          Experimental prototype — not medical advice, not a diagnosis. Acting on warnings is your
          decision.
        </Text>

        {/* Static guidance is ALWAYS shown, independent of dispatch (Req 11.8). */}
        <View style={styles.guidanceCard}>
          <Text style={styles.guidanceTitle}>Call emergency services directly</Text>
          <Text style={styles.guidanceBody}>
            {guidance ||
              "If you may be having a heart attack or stroke, call your local emergency services number immediately. Do not wait for this app."}
          </Text>
        </View>

        {settings.isError ? (
          <View style={styles.card}>
            <Text style={styles.disabledTitle}>Couldn’t load emergency settings</Text>
            <Pressable onPress={() => settings.refetch()} accessibilityRole="button">
              <Text style={styles.body}>Retry</Text>
            </Pressable>
          </View>
        ) : settings.isPending ? (
          <ActivityIndicator color={theme.colors.accent} />
        ) : !enabled ? (
          <View style={styles.card}>
            <Text style={styles.disabledTitle}>Emergency dispatch is off</Text>
            <Text style={styles.body}>
              This optional feature is disabled. Enable it in Settings to use app-assisted dispatch.
              The static guidance above always applies.
            </Text>
          </View>
        ) : evaluate.isError ? (
          <View style={styles.card}>
            <Text style={styles.disabledTitle}>Unable to evaluate emergency routing</Text>
            <Text style={styles.body}>{(evaluate.error as Error).message}</Text>
            <Pressable onPress={retryEvaluation} accessibilityRole="button">
              <Text style={styles.body}>Retry evaluation</Text>
            </Pressable>
          </View>
        ) : location.loading || careProfile.isPending || evaluate.isPending ? (
          <ActivityIndicator color={theme.colors.accent} style={styles.loader} />
        ) : decision && decision.recipientName ? (
          <DecisionPreview decision={decision} approximate={location.approximate} onStart={() => setConfirming(true)} />
        ) : (
          <View style={styles.card}>
            <Text style={styles.body}>
              No routing decision is available. The guidance above still applies.
            </Text>
          </View>
        )}

        {lastResult ? (
          <View style={styles.resultCard}>
            <Text style={styles.resultText}>{lastResult}</Text>
          </View>
        ) : null}

        <Text style={styles.h2}>Dispatch history</Text>
        {history.isLoading ? (
          <ActivityIndicator color={theme.colors.accent} />
        ) : history.isError ? (
          <View style={styles.card}>
            <Text style={styles.body}>Couldn’t load dispatch history.</Text>
            <Pressable onPress={() => history.refetch()} accessibilityRole="button">
              <Text style={styles.body}>Retry history</Text>
            </Pressable>
          </View>
        ) : (
          <DispatchHistoryList events={history.data ?? []} />
        )}
      </ScrollView>

      {enabled && !evaluate.isPending && !evaluate.isError && decision && decision.recipientName ? (
        <EmergencyConfirmDialog
          visible={confirming}
          recipientName={decision.recipientName}
          channel={channel}
          onConfirm={onConfirm}
          onCancel={() => setConfirming(false)}
          busy={dispatch.isPending}
        />
      ) : null}
    </SafeAreaView>
  );
}

function DecisionPreview({
  decision,
  approximate,
  onStart,
}: {
  decision: EmergencyDecision;
  approximate: boolean;
  onStart: () => void;
}) {
  const payload = decision.payload as
    | { location?: { lat?: number; lon?: number; approximate?: boolean }; findingSummary?: string }
    | null
    | undefined;
  const loc = payload?.location;
  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.cardTitle}>Would contact</Text>
        <SimulatedDispatchBadge channel={decision.channel ?? "simulated"} />
      </View>
      <Text style={styles.recipient}>{decision.recipientName}</Text>
      <Text style={styles.meta}>
        Routing:{" "}
        {decision.routingReason === "preferred_doctor_reachable"
          ? "preferred doctor (reachable)"
          : "nearest capable hospital"}
      </Text>

      <Text style={styles.sectionLabel}>Payload preview</Text>
      {loc && loc.lat != null && loc.lon != null ? (
        <Text style={styles.meta}>
          Location: {loc.lat.toFixed(4)}, {loc.lon.toFixed(4)}
          {approximate || loc.approximate ? " (approximate)" : ""}
        </Text>
      ) : null}
      {payload?.findingSummary ? <Text style={styles.summary}>{payload.findingSummary}</Text> : null}

      <Pressable style={styles.startBtn} onPress={onStart} accessibilityRole="button">
        <Text style={styles.startText}>Start dispatch…</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  h2: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700", marginTop: theme.spacing(2) },
  notice: { color: theme.colors.experimental, fontSize: theme.font.caption, fontWeight: "600" },
  guidanceCard: {
    backgroundColor: theme.colors.surfaceAlt,
    borderLeftWidth: 4,
    borderLeftColor: theme.colors.danger,
    borderRadius: theme.radius.md,
    padding: theme.spacing(3),
    gap: theme.spacing(1),
  },
  guidanceTitle: { color: theme.colors.danger, fontSize: theme.font.body, fontWeight: "700" },
  guidanceBody: { color: theme.colors.textPrimary, fontSize: theme.font.body, lineHeight: 20 },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(3),
    gap: theme.spacing(1),
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardTitle: { color: theme.colors.textSecondary, fontSize: theme.font.caption, textTransform: "uppercase" },
  recipient: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700" },
  disabledTitle: { color: theme.colors.warn, fontSize: theme.font.body, fontWeight: "700" },
  body: { color: theme.colors.textSecondary, fontSize: theme.font.body, lineHeight: 20 },
  meta: { color: theme.colors.textSecondary, fontSize: theme.font.caption },
  sectionLabel: {
    color: theme.colors.textPrimary,
    fontSize: theme.font.caption,
    fontWeight: "700",
    marginTop: theme.spacing(2),
    textTransform: "uppercase",
  },
  summary: { color: theme.colors.experimental, fontSize: theme.font.caption, marginTop: theme.spacing(1), lineHeight: 18 },
  startBtn: {
    backgroundColor: theme.colors.danger,
    borderRadius: theme.radius.md,
    paddingVertical: theme.spacing(3),
    alignItems: "center",
    marginTop: theme.spacing(2),
  },
  startText: { color: theme.colors.bg, fontSize: theme.font.body, fontWeight: "700" },
  loader: { marginVertical: theme.spacing(4) },
  resultCard: {
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: theme.radius.md,
    padding: theme.spacing(3),
  },
  resultText: { color: theme.colors.textPrimary, fontSize: theme.font.body },
});
