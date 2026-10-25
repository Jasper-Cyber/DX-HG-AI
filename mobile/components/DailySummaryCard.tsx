import { Text, View, StyleSheet } from "react-native";
import Svg, { Circle } from "react-native-svg";
import type { Reading } from "@/api/types";
import { hasUsableValue, formatSampleTime } from "@/utils/metrics";
import { Icon } from "./Icon";
import { theme, metricPalette } from "@/theme";
export function DailySummaryCard({ metric, reading }: { metric: "activity" | "sleep"; reading?: Reading }) {
  const palette = metricPalette[metric];
  const active = metric === "activity";
  const value = hasUsableValue(reading) ? reading!.value : null;
  const progress = value === null ? 0 : Math.max(0, Math.min(1, value / 8000));
  return <View style={[s.card, { borderWidth: 1, borderColor: palette.border, borderTopWidth: 3, borderTopColor: palette.ink }]}>
    <View style={s.copy}><View style={s.row}><Icon name={active ? "activity" : "moon"} size={17} color={palette.ink} /><Text style={s.label}>{active ? "Activity" : "Sleep"}</Text></View>
      <Text style={[s.number, { color: palette.ink }]}>{value === null ? "—" : active ? Math.round(value).toLocaleString() : value.toFixed(1)}<Text style={s.unit}>{active ? " / 8,000 steps" : " hours slept"}</Text></Text>
      <Text style={[s.note, { color: palette.ink }]}>{value === null ? "No usable reading" : active ? `${Math.round(progress * 100)}% of demo activity target` : "Synthetic sleep estimate"}</Text>
      <Text style={s.timestamp}>{formatSampleTime(reading?.timestamp)}</Text>
    </View>
    {active ? <View style={s.ring}><Svg width={66} height={66} viewBox="0 0 66 66"><Circle cx={33} cy={33} r={27} stroke={theme.colors.surfaceAlt} strokeWidth={5} fill="none" /><Circle cx={33} cy={33} r={27} stroke={palette.ink} strokeWidth={5} fill="none" strokeDasharray={`${170 * progress} 170`} rotation={-90} origin="33,33" strokeLinecap="round" /></Svg><Text style={s.percent}>{value === null ? "—" : `${Math.round(progress * 100)}%`}</Text></View>
    : <View style={[s.moon, { backgroundColor: palette.soft }]}><Icon name="moon" size={30} color={palette.ink} /></View>}
  </View>;
}
const s = StyleSheet.create({
  timestamp: { fontFamily: theme.type.body, fontSize: 11, color: theme.colors.textSecondary, marginTop: 8 },
  card: { backgroundColor: theme.colors.surface, borderRadius: 16, padding: 17, flexDirection: "row", alignItems: "center", gap: 10 },
  copy: { flex: 1 }, row: { flexDirection: "row", alignItems: "center", gap: 7 },
  label: { fontFamily: theme.type.heading, fontSize: 16, color: theme.colors.textPrimary },
  number: { fontFamily: theme.type.heading, fontSize: 25, color: theme.colors.textPrimary, marginTop: 8 },
  unit: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary },
  note: { color: theme.colors.accentGreen, fontFamily: theme.type.body, fontSize: 10, marginTop: 4 },
  ring: { alignItems: "center", justifyContent: "center" }, percent: { position: "absolute", fontFamily: theme.type.mono, fontSize: 10, color: theme.colors.textPrimary },
  moon: { width: 60, height: 60, borderRadius: 32, backgroundColor: theme.colors.surfaceAlt, alignItems: "center", justifyContent: "center" },
});
