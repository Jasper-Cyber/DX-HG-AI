import { ChartLegend } from "./ChartLegend";
import { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import type { MetricType, Reading } from "@/api/types";
import { healthTrends, type DailySummary } from "@/utils/healthTrends";
import { METRIC_META } from "@/utils/metrics";
import { theme, metricPalette, chartCompanion } from "@/theme";
import { Icon } from "./Icon";

export function HealthTrendDetails({ readings, metric }: { readings: Reading[]; metric: MetricType }) {
  const palette = metricPalette[metric];
  const [showMethod, setShowMethod] = useState(false);
  const [days, setDays] = useState<7 | 30>(7);
  const [selected, setSelected] = useState<string | null>(null);
  const summary = useMemo(() => healthTrends(readings, metric, days), [readings, metric, days]);
  if (!summary) return <Text style={s.muted}>Start the simulator to build trend history.</Text>;
  const unit = METRIC_META[metric].unit;
  const fmt = (n: number | null) => n === null ? "—" : n.toFixed(1);
  const selectedDay = summary.current.find(d => d.date === selected) ?? summary.yesterday;
  const maximum = Math.max(1, ...summary.current.flatMap(d => d.max === null ? [] : [d.max]));
  const period = days === 7 ? "week" : "30 days";
  const changeText = summary.change === null ? "Not enough comparable history" : `${summary.change > 0 ? "↑" : summary.change < 0 ? "↓" : "↔"} ${Math.abs(summary.change).toFixed(1)} ${unit}${summary.percentChange !== null ? ` (${Math.abs(summary.percentChange).toFixed(1)}%)` : ""}`;
  return <View style={s.stack}>
    <View style={s.heading}><Icon name="chart" size={18} color={palette.ink} /><Text style={s.title}>Trends</Text></View>
    <View style={s.tabs}>{([7, 30] as const).map(n => <Pressable key={n} accessibilityRole="button" accessibilityLabel={n === 7 ? "Weekly trend" : "Monthly trend"} accessibilityState={{ selected: days === n }} onPress={() => { setDays(n); setSelected(null); }} style={[s.tab, days === n && { backgroundColor: palette.ink }]}><Text style={[s.tabText, days === n && { color: theme.colors.onAccent }]}>{n === 7 ? "Weekly" : "Monthly"}</Text></Pressable>)}</View>
    <View style={s.panel}>
      <View style={s.between}><Text style={s.title}>{days === 7 ? "Weekly trend" : "Monthly trend"}</Text><Text style={s.muted}>{unit}</Text></View>
      <Text style={s.muted}>Daily averages · last {days} complete UTC days</Text>
      <Text style={s.scale}>0–{maximum.toFixed(0)} {unit}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={days === 30}><View style={[s.bars, { width: days === 30 ? 1320 : 308 }]}>{summary.current.map((d, i) => <DailyBar rangeColor={chartCompanion[metric]} color={palette.ink} key={d.date} day={d} index={i} count={days} maximum={maximum} selected={d.date === selectedDay.date} onPress={() => setSelected(d.date)} />)}</View></ScrollView>
      <View style={s.between}><Text style={s.small}>{summary.current[0].date.slice(5)}</Text><Text style={s.small}>{summary.yesterday.date.slice(5)}</Text></View>
      <ChartLegend items={[{ label: "Daily average", color: palette.ink, mark: "bar" }, { label: "Min–max range", color: chartCompanion[metric] }]} />
      <Text style={s.tip}>Bars show the average; vertical lines show min–max. Tap a day for its values, or scroll across the month. A dash means no data.</Text>
      <View style={s.selection}><Text style={[s.selectionDate, { color: palette.ink }]}>{selectedDay.date}</Text><View style={s.between}>{[["Min", selectedDay.min], ["Average", selectedDay.mean], ["Max", selectedDay.max]].map(([label, value]) => <View key={String(label)}><Text style={s.small}>{label}</Text><Text style={s.number}>{fmt(value as number | null)}</Text></View>)}</View><Text style={s.small}>{selectedDay.count} usable samples · {unit}</Text></View>
      <View style={s.between}><Text style={s.muted}>Period average</Text><Text style={s.number}>{fmt(summary.average)} <Text style={s.small}>{unit}</Text></Text></View>
      <Text style={[s.change, { color: palette.ink }]}>{changeText}</Text><Text style={s.small}>Compared with the preceding {days} days. Direction describes the numbers, not health improvement.</Text>
    </View>
    <View style={s.panel}><View style={s.heading}><Icon name="clock" size={18} color={palette.ink} /><Text style={s.title}>History</Text></View>
      <View style={s.historyRow}><View><Text style={s.muted}>Last complete day</Text><Text style={s.small}>{summary.yesterday.date}</Text></View><Text style={s.number}>{fmt(summary.yesterday.mean)} <Text style={s.small}>{unit}</Text></Text></View>
      <View style={s.historyRow}><Text style={s.muted}>This {period}</Text><Text style={s.number}>{fmt(summary.average)} <Text style={s.small}>{unit}</Text></Text></View>
      <View style={s.historyRow}><Text style={s.muted}>Previous {period}</Text><Text style={s.number}>{fmt(summary.previousAverage)} <Text style={s.small}>{unit}</Text></Text></View>
    </View>
    <Pressable onPress={() => setShowMethod(!showMethod)} accessibilityRole="button" accessibilityState={{ expanded: showMethod }} style={({ pressed }) => [s.methodButton, pressed && { backgroundColor: palette.soft }]}><Text style={s.methodLabel}>{showMethod ? "Hide forecast & methodology −" : "Forecast & methodology +"}</Text></Pressable>
    {showMethod && <View style={[s.panel, { backgroundColor: palette.soft }]}><View style={s.between}><Text style={s.title}>Forecast</Text><Text style={[s.badge, { color: palette.ink }]}>Experimental estimate</Text></View>
      {summary.forecast ? <><Text style={s.muted}>Estimated daily average · {summary.forecast.date}</Text><Text style={[s.forecastValue, { color: palette.ink }]}>{fmt(summary.forecast.value)} <Text style={s.muted}>{unit}</Text></Text><Text style={s.small}>A straight-line extrapolation of {summary.forecast.daysUsed} recent daily averages. Not a measured value or a validated clinical prediction. Real readings may differ.</Text></> : <Text style={s.muted}>No estimate available. At least 4 of the last 7 days, including the most recent day, need 12 usable hourly samples. Impossible estimates are suppressed.</Text>}
    </View>}
    {showMethod && <Text style={s.small}>The incomplete simulation day ({summary.excludedPartialDate}) is excluded from comparisons. Low-quality and missing samples are excluded throughout.</Text>}
  </View>;
}
function DailyBar({ rangeColor, color, day, index, count, maximum, selected, onPress }: { rangeColor: string; color: string; day: DailySummary; index: number; count: number; maximum: number; selected: boolean; onPress: () => void }) {
  const height = day.mean === null ? 0 : day.mean / maximum * 100;
  return <Pressable onPress={onPress} style={[s.barColumn, selected && { borderBottomWidth: 2, borderBottomColor: color }]} accessibilityRole="button" accessibilityState={{ selected }} accessibilityLabel={`${day.date}: ${day.mean === null ? "No data" : `average ${day.mean.toFixed(1)}, minimum ${day.min?.toFixed(1)}, maximum ${day.max?.toFixed(1)}`}`}>
    <View style={s.barTrack}>
      {day.min !== null && day.max !== null && <View pointerEvents="none" style={[s.rangeLine, { backgroundColor: rangeColor, bottom: `${day.min / maximum * 100}%`, height: `${Math.max((day.max - day.min) / maximum * 100, 1)}%` }]} />}
      {day.mean === null ? <Text style={s.small}>—</Text> : <View style={[s.bar, { height: `${Math.max(height, 1)}%`, backgroundColor: color }]} />}</View>
    {(count === 7 || count === 30) && <Text style={s.barLabel}>{day.date.slice(8)}</Text>}
  </Pressable>;
}
const s = StyleSheet.create({
  methodButton: { minHeight: 48, justifyContent: "center", padding: 12, borderRadius: 12, borderWidth: 1, borderColor: theme.colors.controlBorder },
  methodLabel: { fontFamily: theme.type.heading, fontSize: 13, color: theme.colors.textPrimary },
  stack: { gap: 14, marginTop: 20 }, heading: { flexDirection: "row", alignItems: "center", gap: 8 },
  title: { fontFamily: theme.type.heading, fontSize: 18, color: theme.colors.textPrimary },
  tabs: { flexDirection: "row", backgroundColor: theme.colors.surfaceAlt, borderRadius: 12, padding: 4, gap: 5 },
  tab: { flex: 1, padding: 11, alignItems: "center", borderRadius: 9 }, active: { backgroundColor: theme.colors.accent },
  tabText: { fontFamily: theme.type.body, fontSize: 13, color: theme.colors.textPrimary },
  panel: { backgroundColor: theme.colors.inset, borderRadius: 15, padding: 15, gap: 10 },
  between: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 8, flexWrap: "wrap" },
  muted: { fontFamily: theme.type.body, fontSize: 12, lineHeight: 19, color: theme.colors.textSecondary },
  small: { fontFamily: theme.type.body, fontSize: 12, lineHeight: 17, color: theme.colors.textSecondary },
  scale: { fontFamily: theme.type.mono, fontSize: 12, color: theme.colors.textSecondary },
  bars: { flexDirection: "row", alignItems: "flex-start", height: 128, gap: 3 },
  barColumn: { flex: 1, height: 128, alignItems: "center" }, barTrack: { height: 106, width: "100%", justifyContent: "flex-end", alignItems: "center", borderBottomWidth: 1, borderColor: theme.colors.border },
  rangeLine: { position: "absolute", right: 0, width: 2, backgroundColor: theme.colors.textSecondary, zIndex: 1 },
  bar: { width: "72%", borderTopLeftRadius: 4, borderTopRightRadius: 4 },
  barLabel: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary, paddingTop: 4 },
  tip: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary },
  selection: { backgroundColor: theme.colors.surface, borderRadius: 10, padding: 12, gap: 8 },
  selectionDate: { fontFamily: theme.type.mono, fontSize: 12, color: theme.colors.accent },
  number: { fontFamily: theme.type.heading, fontSize: 20, color: theme.colors.textPrimary },
  change: { color: theme.colors.accent, fontFamily: theme.type.heading, fontSize: 15 },
  historyRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, paddingVertical: 7, borderBottomWidth: 1, borderColor: theme.colors.border },
  forecast: { backgroundColor: theme.colors.accentSoft }, badge: { fontFamily: theme.type.body, color: theme.colors.accent, fontSize: 10 },
  forecastValue: { fontFamily: theme.type.heading, fontSize: 32, color: theme.colors.accent },
});
