import { StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import type { AlertState } from "@/api/types";
import { alertStateMeta } from "@/utils/alerts";
import { theme } from "@/theme";
import { Icon } from "./Icon";
export function MonitoringStatusCard({ state, title }: { state: AlertState; title?: string }) {
  const meta = alertStateMeta(state);
  return <LinearGradient colors={[theme.colors.accentSoft, theme.colors.surface, theme.colors.accentSoft]} start={{ x: 0, y: 1 }} end={{ x: 1, y: 0 }} style={s.card}>
    <View style={s.row}><Icon name="shield" size={14} color={meta.color} /><Text style={[s.status, { color: meta.color }]}>{meta.label.toUpperCase()}</Text></View>
    <Text style={s.title}>{title ?? meta.defaultTitle}</Text>

    <View style={s.footer}><Icon name="pulse" size={15} /><Text style={s.meta}>Simulation analysis</Text><View style={{ flex: 1 }} /><Icon name="shield" size={12} /><Text style={s.meta}>EXPERIMENTAL</Text></View>
  </LinearGradient>;
}
const s = StyleSheet.create({
  card: { borderRadius: 16, padding: 15, gap: 9, overflow: "hidden" },
  row: { flexDirection: "row", alignItems: "center", gap: 6 },
  status: { fontFamily: theme.type.mono, fontSize: 11, letterSpacing: .6 },
  title: { fontFamily: theme.type.heading, fontSize: 18, color: theme.colors.textPrimary },
  body: { fontFamily: theme.type.body, fontSize: 12, lineHeight: 19, color: theme.colors.textSecondary },
  footer: { flexDirection: "row", gap: 6, alignItems: "center", paddingTop: 12, marginTop: 4, borderTopWidth: 1, borderTopColor: theme.colors.border },
  meta: { fontFamily: theme.type.mono, fontSize: 11, color: theme.colors.pale },
});
