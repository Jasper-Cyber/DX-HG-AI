import { Icon } from "@/components/Icon";
import { ExperimentalNotice } from "@/components/ExperimentalNotice";
import { AppHeader } from "@/components/AppHeader";
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
      <AppHeader title="Simulator" />
      <ScrollView contentContainerStyle={styles.content}>



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

            <Text style={styles.sectionLabel}>PRESET TEST SCENARIOS</Text>
            <ScenarioPicker value={state.scenario as Scenario} onChange={onSelect} disabled={busy} />

            <View style={styles.deck}>
            <View style={styles.deckHeader}><Icon name="play" size={17} /><Text style={styles.deckTitle}>Telemetry deck</Text><Text style={styles.deckBadge}>{running ? "STREAMING" : "PAUSED"}</Text></View>
            <View style={styles.controls}>
              {running ? (
                <Pressable
                  style={[styles.btn, styles.btnWarn, busy && styles.btnDisabled]}
                  onPress={() => control.mutate("pause")}
                  disabled={busy}
                  accessibilityRole="button"
                >
                  <Icon name="pause" color={theme.colors.onAccent} size={18} /><Text style={styles.btnText}>Pause</Text>
                </Pressable>
              ) : (
                <Pressable
                  style={[styles.btn, styles.btnPrimary, busy && styles.btnDisabled]}
                  onPress={() => control.mutate("start")}
                  disabled={busy}
                  accessibilityRole="button"
                >
                  <Icon name="play" color={theme.colors.onAccent} size={18} /><Text style={styles.btnText}>{state.cursorTs ? "Resume" : "Start"}</Text>
                </Pressable>
              )}
              <Pressable
                style={[styles.btn, styles.btnGhost, busy && styles.btnDisabled]}
                onPress={() => control.mutate("reset")}
                disabled={busy}
                accessibilityRole="button"
              >
                <Icon name="reset" color={theme.colors.textPrimary} size={18} /><Text style={styles.btnGhostText}>Reset</Text>
              </Pressable>
            </View>

            <View style={styles.speedRow}><Text style={styles.sectionLabel}>DEMO PLAYBACK</Text><Text style={styles.speed}>1 simulated hour / 5 sec</Text></View>
            </View>
            <View style={styles.deck}><View style={styles.deckHeader}><Icon name="sliders" size={18} /><Text style={styles.deckTitle}>Simulation overview</Text></View>
              <View style={styles.detailRow}><Text style={styles.sub}>Selected scenario</Text><Text style={styles.detailValue}>Scenario {state.scenario}</Text></View>
              <View style={styles.detailRow}><Text style={styles.sub}>Generation seed</Text><Text style={styles.detailValue}>{state.seed}</Text></View>
              <View style={styles.detailRow}><Text style={styles.sub}>Analysis</Text><Text style={styles.detailValue}>{running ? "Automatic" : "Paused"}</Text></View>
              <Text style={styles.sub}>Changing scenario starts a fresh dataset. Reset clears current readings; saved alerts stay in History.</Text>
            </View>
            {control.isError || setScenario.isError ? (
              <Text style={styles.actionError}>That action failed. Check the backend and try again.</Text>
            ) : null}
          </>
        ) : null}
        <ExperimentalNotice />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  sectionLabel: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: 11, letterSpacing: 1, marginVertical: 6 },
  deck: { backgroundColor: theme.colors.surface, borderRadius: 17, padding: 17, gap: 12 },
  deckHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  deckTitle: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 17, flex: 1 },
  deckBadge: { color: theme.colors.accentGreen, backgroundColor: theme.colors.accentSoft, borderRadius: 6, padding: 5, fontFamily: theme.type.mono, fontSize: 11 },
  speedRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" },
  speed: { color: theme.colors.accentGreen, fontFamily: theme.type.mono, fontSize: 11 },
  detailRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 12, backgroundColor: theme.colors.inset, borderRadius: 9 },
  detailValue: { color: theme.colors.pale, fontFamily: theme.type.mono, fontSize: 11 },
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), paddingTop: 4, paddingBottom: 28, gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: theme.font.h1, fontWeight: "700" },
  sub: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: theme.font.body },
  statusRow: { backgroundColor: theme.colors.surface, borderRadius: 12, padding: 14, flexDirection: "row", alignItems: "center", gap: theme.spacing(2) },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  statusText: { color: theme.colors.textPrimary, fontFamily: theme.type.body, fontSize: theme.font.body, fontWeight: "600" },
  controls: { flexDirection: "row", gap: theme.spacing(3), marginTop: theme.spacing(1) },
  btn: { flex: 1, paddingVertical: theme.spacing(3), borderRadius: theme.radius.md, alignItems: "center", gap: 9 },
  btnPrimary: { backgroundColor: theme.colors.accent },
  btnWarn: { backgroundColor: theme.colors.warn },
  btnGhost: { borderWidth: 1, borderColor: theme.colors.border, backgroundColor: theme.colors.surface },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: theme.colors.onAccent, fontWeight: "800", fontFamily: theme.type.body, fontSize: theme.font.body },
  btnGhostText: { color: theme.colors.textPrimary, fontWeight: "700", fontFamily: theme.type.body, fontSize: theme.font.body },
  actionError: { color: theme.colors.danger, fontFamily: theme.type.mono, fontSize: theme.font.caption },
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
