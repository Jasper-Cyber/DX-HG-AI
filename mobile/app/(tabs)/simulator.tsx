import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import type { Scenario } from "@/api/types";
import { useScenario, useSetScenario, useSimulatorControl } from "@/api/hooks";
import { ScenarioPicker } from "@/components/ScenarioPicker";
import { SimulatedDataRibbon } from "@/components/SimulatedDataRibbon";
import { theme } from "@/theme";

/**
 * Simulator (Task 17, Req 2.6).
 *
 * Scenario picker (A/B/C) plus Start / Pause / Reset controls wired to the
 * backend. Controls disable while a request is in flight so the user can't
 * fire overlapping transitions.
 */
export default function SimulatorScreen() {
  const scenario = useScenario();
  const setScenario = useSetScenario();
  const control = useSimulatorControl();

  const state = scenario.data;
  const running = state?.status === "running";
  const busy = setScenario.isPending || control.isPending;

  const onSelect = (s: Scenario) => setScenario.mutate(s);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.h1}>Simulator</Text>
        <Text style={styles.sub}>Generate synthetic physiological data for the demo.</Text>

        {scenario.isLoading && !state ? (
          <View style={styles.centerCard}>
            <ActivityIndicator color={theme.colors.accent} />
            <Text style={styles.muted}>Loading simulator state…</Text>
          </View>
        ) : scenario.isError ? (
          <View style={styles.centerCard}>
            <Text style={styles.errorTitle}>Can’t reach the backend</Text>
            <Text style={styles.muted}>Make sure the API is running, then retry.</Text>
            <Pressable style={styles.retry} onPress={() => scenario.refetch()} accessibilityRole="button">
              <Text style={styles.retryText}>Retry</Text>
            </Pressable>
          </View>
        ) : state ? (
          <>
            <View style={styles.statusRow}>
              <View style={[styles.statusDot, { backgroundColor: running ? theme.colors.accentGreen : theme.colors.textSecondary }]} />
              <Text style={styles.statusText}>
                {running ? "Running" : "Paused"} · Scenario {state.scenario}
              </Text>
            </View>

            <ScenarioPicker value={state.scenario as Scenario} onChange={onSelect} disabled={busy} />

            <View style={styles.controls}>
              {running ? (
                <Pressable
                  style={[styles.btn, styles.btnWarn, busy && styles.btnDisabled]}
                  onPress={() => control.mutate("pause")}
                  disabled={busy}
                  accessibilityRole="button"
                >
                  <Text style={styles.btnText}>Pause</Text>
                </Pressable>
              ) : (
                <Pressable
                  style={[styles.btn, styles.btnPrimary, busy && styles.btnDisabled]}
                  onPress={() => control.mutate("start")}
                  disabled={busy}
                  accessibilityRole="button"
                >
                  <Text style={styles.btnText}>Start</Text>
                </Pressable>
              )}
              <Pressable
                style={[styles.btn, styles.btnGhost, busy && styles.btnDisabled]}
                onPress={() => control.mutate("reset")}
                disabled={busy}
                accessibilityRole="button"
              >
                <Text style={styles.btnGhostText}>Reset</Text>
              </Pressable>
            </View>

            {control.isError || setScenario.isError ? (
              <Text style={styles.actionError}>That action failed. Check the backend and try again.</Text>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  sub: { color: theme.colors.textSecondary, fontSize: theme.font.body },
  statusRow: { flexDirection: "row", alignItems: "center", gap: theme.spacing(2) },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  statusText: { color: theme.colors.textPrimary, fontSize: theme.font.body, fontWeight: "600" },
  controls: { flexDirection: "row", gap: theme.spacing(3), marginTop: theme.spacing(1) },
  btn: { flex: 1, paddingVertical: theme.spacing(3), borderRadius: theme.radius.md, alignItems: "center" },
  btnPrimary: { backgroundColor: theme.colors.accentGreen },
  btnWarn: { backgroundColor: theme.colors.warn },
  btnGhost: { borderWidth: 1, borderColor: theme.colors.border, backgroundColor: theme.colors.surface },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: theme.colors.bg, fontWeight: "800", fontSize: theme.font.body },
  btnGhostText: { color: theme.colors.textPrimary, fontWeight: "700", fontSize: theme.font.body },
  actionError: { color: theme.colors.danger, fontSize: theme.font.caption },
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
