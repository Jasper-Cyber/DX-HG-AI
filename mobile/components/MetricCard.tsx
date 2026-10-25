import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { MetricType, Reading } from "@/api/types";
import { METRIC_META, formatMetricValue, hasUsableValue, qualityLabel, summarizeMetric, formatSampleTime } from "@/utils/metrics";
import { healthTrends } from "@/utils/healthTrends";
import { theme, metricPalette } from "@/theme";
import { HealthTrendDetails } from "./HealthTrendDetails";
import { MiniTrend } from "./MiniTrend";
import { Icon, type IconName } from "./Icon";
const icons: Record<MetricType, IconName> = { vo2max: "activity", hr: "heart", hrv: "pulse", spo2: "drop", rhythm: "pulse", activity: "activity", sleep: "moon" };

/** A scannable reading first; sample quality and deeper analysis on request. */
export function MetricCard({ metric, reading, series, readings, historyReadings, windowLabel = "Selected period" }: {
  metric: MetricType; reading?: Reading; series?: (number | null)[]; readings?: Reading[]; historyReadings?: Reading[]; windowLabel?: string;
}) {
  const meta = METRIC_META[metric];
  const palette = metricPalette[metric];
  const [expanded, setExpanded] = useState(false);
  const [focused, setFocused] = useState(false);
  const history = historyReadings ?? readings ?? [];
  const trend = useMemo(() => healthTrends(history, metric), [history, metric]);
  const usable = hasUsableValue(reading);
  const value = formatMetricValue(usable ? reading!.value : null, metric);
  const quality = reading ? qualityLabel(reading.quality) : "No data";
  const rhythm = metric === "rhythm";
  const summary = summarizeMetric(readings ?? (reading ? [reading] : []), metric);
  const points = series ?? summary.rows.map(r => hasUsableValue(r) ? r.value : null);
  const stat = (n: number | null) => n === null ? "—" : n.toFixed(1);
  return <View style={s.card}>
    <View style={s.header}>
      <View style={[s.icon, { backgroundColor: palette.soft }]}><Icon name={icons[metric]} size={20} color={palette.ink} /></View>
      <View style={s.heading}><Text accessibilityRole="header" style={s.label}>{meta.label}</Text><Text style={s.caption}>Latest synthetic reading</Text></View>
    </View>
    <View style={s.readingRow}>
      <View style={s.reading}><View style={s.valueRow}><Text style={[s.value, { color: palette.ink }, rhythm && s.rhythm]}>{value}</Text>{usable && !!meta.unit && <Text style={s.unit}>{meta.unit}</Text>}</View>{!usable && <Text style={s.quality}>{quality}</Text>}</View>
      {summary.validCount > 0 && <View style={s.preview} accessible accessibilityLabel={`${meta.label} trend, ${windowLabel}. Minimum ${stat(summary.min)}, maximum ${stat(summary.max)}${meta.unit ? ` ${meta.unit}` : ""}. Gaps indicate unavailable readings.`}><MiniTrend values={points} color={palette.ink} height={52} /><Text style={s.previewLabel}>{windowLabel}</Text></View>}
    </View>
    {!rhythm && <Text style={s.direction}>{trend?.change == null ? "Weekly comparison building" : `${trend.change > 0 ? "↑" : trend.change < 0 ? "↓" : "↔"} ${Math.abs(trend.change).toFixed(1)} ${meta.unit} vs previous week`}</Text>}
    {rhythm && <Text style={s.direction}>0 = regular · 1 = irregular flag</Text>}
    <Pressable onPress={() => setExpanded(!expanded)} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} accessibilityRole="button" accessibilityLabel={`${expanded ? "Collapse" : "Expand"} ${meta.label} details`} accessibilityState={{ expanded }} style={({ pressed }) => [s.disclosure, { borderColor: focused ? palette.ink : theme.colors.border, backgroundColor: pressed || focused ? palette.soft : theme.colors.surface }]}>
      <Text style={s.caption}>{windowLabel}</Text><Text style={[s.detailsLink, { color: palette.ink }]}>{expanded ? "Close details −" : "Explore trend +"}</Text>
    </Pressable>
    {expanded && <View style={s.details}>
      <Text style={s.caption}>Latest sample · {formatSampleTime(reading?.timestamp)}</Text>
      {summary.validCount > 0 && <View style={[s.stats, { backgroundColor: palette.soft }]}>{(rhythm ? [["Flagged", `${summary.flagged}`], ["Usable", `${summary.validCount}`], ["Flag rate", `${Math.round(summary.flagged / summary.validCount * 100)}%`]] : [["Minimum", stat(summary.min)], ["Average", stat(summary.mean)], ["Maximum", stat(summary.max)]]).map(([label, number]) => <View key={label} style={s.stat}><Text style={s.caption}>{label}</Text><Text style={s.statValue}>{number}</Text></View>)}</View>}
      <Text style={s.caption}>{summary.validCount} of {summary.totalCount} samples usable{summary.validCount < summary.totalCount ? ` · ${summary.totalCount - summary.validCount} excluded` : ""}. Gaps indicate unavailable readings.</Text>
      {!rhythm && <HealthTrendDetails readings={history} metric={metric} />}
    </View>}
  </View>;
}
const s = StyleSheet.create({
  card: { width: "100%", backgroundColor: theme.colors.surface, borderRadius: 24, borderWidth: 1, borderColor: theme.colors.border, padding: 20 },
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  heading: { flex: 1 }, icon: { padding: 10, borderRadius: 14 },
  label: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 19 },
  caption: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 12, lineHeight: 19 },
  readingRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 16, marginTop: 18 },
  reading: { flexGrow: 1 }, valueRow: { flexDirection: "row", alignItems: "baseline", flexWrap: "wrap", gap: 6 },
  value: { fontFamily: theme.type.heading, fontSize: 44, letterSpacing: -1.5 }, rhythm: { fontSize: 29, letterSpacing: -.5 },
  unit: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 14 },
  preview: { flex: 1, minWidth: 105, maxWidth: 180 },
  previewLabel: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 12, textAlign: "right", marginTop: 5 },
  quality: { color: theme.colors.warn, fontFamily: theme.type.body, fontSize: 13 },
  direction: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 13, lineHeight: 20, marginTop: 10 },
  disclosure: { minHeight: 48, flexDirection: "row", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8, borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, marginTop: 16 },
  detailsLink: { fontFamily: theme.type.heading, fontSize: 13 }, details: { marginTop: 18, gap: 12 },
  stats: { flexDirection: "row", borderRadius: 12, padding: 12, gap: 10 },
  stat: { flex: 1 }, statValue: { fontFamily: theme.type.heading, color: theme.colors.textPrimary, fontSize: 21, marginTop: 5 },
});
