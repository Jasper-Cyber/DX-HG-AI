import { StyleSheet, Text, View } from "react-native";
import type { Reading } from "@/api/types";
import { healthTrends } from "@/utils/healthTrends";
import { METRIC_META } from "@/utils/metrics";
import { theme, metricPalette } from "@/theme";
export function TrendComparisonList({ readings }: { readings: Reading[] }) {
  return <View style={s.card}><Text style={s.title}>Trending data</Text><Text style={s.subtitle}>Previous 7 days → latest 7 complete days</Text>{(["vo2max", "hr", "hrv", "spo2"] as const).map(metric => {
    const result = healthTrends(readings, metric);
    const meta = METRIC_META[metric];
    const palette = metricPalette[metric];
    return <View key={metric} style={[s.row, { backgroundColor: palette.soft, borderLeftWidth: 3, borderLeftColor: palette.ink }]}><Text style={[s.label, { color: palette.ink }]}>{meta.label}</Text>{result?.change != null ? <View style={s.values}><Text style={s.old}>{result.previousAverage!.toFixed(1)}</Text><Text style={[s.arrow, { color: palette.ink }]}>{result.change > 0 ? "↗" : result.change < 0 ? "↘" : "→"}</Text><Text style={[s.current, { color: palette.ink }]}>{result.average!.toFixed(1)} <Text style={s.unit}>{meta.unit}</Text></Text></View> : <Text style={s.subtitle}>Building history</Text>}</View>;
  })}<Text style={s.subtitle}>Arrows show numerical change, not a health assessment.</Text></View>;
}
const s = StyleSheet.create({
  card: { backgroundColor: theme.colors.surface, borderRadius: 17, borderWidth: 1, borderColor: theme.colors.border, padding: 16, gap: 10 },
  title: { fontFamily: theme.type.heading, fontSize: 18, color: theme.colors.textPrimary },
  subtitle: { fontFamily: theme.type.body, fontSize: 11, lineHeight: 17, color: theme.colors.textSecondary },
  row: { backgroundColor: theme.colors.inset, borderRadius: 10, padding: 12, gap: 10 },
  label: { fontFamily: theme.type.body, fontSize: 13, color: theme.colors.textPrimary },
  values: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  old: { fontFamily: theme.type.heading, fontSize: 22, color: theme.colors.textSecondary },
  arrow: { color: theme.colors.accent, fontSize: 22 },
  current: { fontFamily: theme.type.heading, fontSize: 22, color: theme.colors.accent },
  unit: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary },
});
