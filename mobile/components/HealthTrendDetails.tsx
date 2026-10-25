import Svg, { Line, Text as SvgText } from "react-native-svg";
import { SelectableChartPoint } from "./SelectableChartPoint";
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
  const period = days === 7 ? "week" : "30 days";
  const changeText = summary.change === null ? "Not enough comparable history" : `${summary.change > 0 ? "↑" : summary.change < 0 ? "↓" : "↔"} ${Math.abs(summary.change).toFixed(1)} ${unit}${summary.percentChange !== null ? ` (${Math.abs(summary.percentChange).toFixed(1)}%)` : ""}`;
  return <View style={s.stack}>
    <View style={s.heading}><Icon name="chart" size={18} color={palette.ink} /><Text style={s.title}>Trends</Text></View>
    <View style={s.tabs}>{([7, 30] as const).map(n => <Pressable key={n} accessibilityRole="button" accessibilityLabel={n === 7 ? "Weekly trend" : "Monthly trend"} accessibilityState={{ selected: days === n }} onPress={() => { setDays(n); setSelected(null); }} style={[s.tab, days === n && { backgroundColor: palette.ink }]}><Text style={[s.tabText, days === n && { color: theme.colors.onAccent }]}>{n === 7 ? "Weekly" : "Monthly"}</Text></Pressable>)}</View>
    <View style={s.panel}>
      <View style={s.between}><Text style={s.title}>{days === 7 ? "Weekly trend" : "Monthly trend"}</Text><Text style={s.muted}>{unit}</Text></View>
      <Text style={s.muted}>Daily averages · last {days} complete UTC days</Text>
      <DailyScatter days={summary.current} color={palette.ink} rangeColor={chartCompanion[metric]} selected={selectedDay.date} onSelect={setSelected} unit={unit} />
      <View style={s.between}><Text style={s.small}>{summary.current[0].date.slice(5)}</Text><Text style={s.small}>{summary.yesterday.date.slice(5)}</Text></View>
      <ChartLegend items={[{ label: "Daily average", color: palette.ink, mark: "dot" }, { label: "Min–max range", color: chartCompanion[metric] }]} />
      <Text style={s.tip}>Dots show daily averages; vertical lines show min–max. Select a dot or date to explore.{days === 30 ? " Scroll across the month to see all 30 days." : ""} Missing days have no dot.</Text>
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
function DailyScatter({ days, color, rangeColor, selected, onSelect, unit }: {
  days: DailySummary[]; color: string; rangeColor: string; selected: string;
  onSelect: (date: string) => void; unit: string;
}) {
  const values = days.flatMap(d => [d.min, d.mean, d.max].filter((v): v is number => v !== null && Number.isFinite(v)));
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const padding = Math.max((max - min) * .15, 1);
  const low = Math.max(0, min - padding), high = max + padding;
  const monthly = days.length > 7;
  const width = 42 + days.length * 44;
  const x = (i: number) => 52 + i * 44;
  const y = (value: number) => 154 - (value - low) / (high - low) * 130;
  const chart = <View style={monthly ? { width } : undefined}>
    <Svg width="100%" height={185} viewBox={`0 0 ${width} 185`} accessibilityLabel={`${monthly ? "Monthly" : "Weekly"} daily-average scatterplot, ${unit}, with minimum and maximum ranges`}>
      {[0, 1, 2, 3].map(i => {
        const value = low + (high - low) * i / 3;
        return <Line key={i} x1={42} x2={width - 12} y1={y(value)} y2={y(value)} stroke={theme.colors.border} strokeDasharray="3 4" />;
      })}
      {[0, 1, 2, 3].map(i => {
        const value = low + (high - low) * i / 3;
        return <SvgText key={i} x={36} y={y(value) + 4} textAnchor="end" fontSize={12} fill={theme.colors.textSecondary}>{value.toFixed(1)}</SvgText>;
      })}
      {days.map((d, i) => d.min !== null && d.max !== null && <Line key={d.date} x1={x(i)} x2={x(i)} y1={y(d.min)} y2={y(d.max)} stroke={rangeColor} strokeWidth={2} />)}
      {days.map((d, i) => d.mean === null ? null : <SelectableChartPoint key={d.date} cx={x(i)} cy={y(d.mean)} r={d.date === selected ? 6 : 4} fill={color} stroke={d.date === selected ? theme.colors.textPrimary : theme.colors.surface} label={`Select ${d.date}, daily average ${d.mean.toFixed(1)} ${unit}`} selected={d.date === selected} onSelect={() => onSelect(d.date)} />)}
    </Svg>
    <View style={[s.scatterDates, { marginLeft: `${30 / width * 100}%`, marginRight: `${12 / width * 100}%` }]}>{days.map(d => <Pressable key={d.date} accessibilityRole="button" accessibilityState={{ selected: d.date === selected }} accessibilityLabel={`${d.date}: ${d.mean === null ? "No data" : `average ${d.mean.toFixed(1)}, minimum ${d.min?.toFixed(1)}, maximum ${d.max?.toFixed(1)}`}`} onPress={() => onSelect(d.date)} style={[s.scatterDate, d.date === selected && { backgroundColor: color }]}><Text style={[s.small, d.date === selected && { color: theme.colors.onAccent }]}>{d.date.slice(8)}</Text>{d.mean === null && <Text style={[s.small, d.date === selected && { color: theme.colors.onAccent }]}>—</Text>}</Pressable>)}</View>
  </View>;
  return monthly ? <ScrollView horizontal showsHorizontalScrollIndicator>{chart}</ScrollView> : chart;
}
const s = StyleSheet.create({
  scatterDates: { flexDirection: "row" },
  scatterDate: { flex: 1, minHeight: 44, alignItems: "center", justifyContent: "center", borderRadius: 8 },
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
  tip: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary },
  selection: { backgroundColor: theme.colors.surface, borderRadius: 10, padding: 12, gap: 8 },
  selectionDate: { fontFamily: theme.type.mono, fontSize: 12, color: theme.colors.accent },
  number: { fontFamily: theme.type.heading, fontSize: 20, color: theme.colors.textPrimary },
  change: { color: theme.colors.accent, fontFamily: theme.type.heading, fontSize: 15 },
  historyRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8, paddingVertical: 7, borderBottomWidth: 1, borderColor: theme.colors.border },
  forecast: { backgroundColor: theme.colors.accentSoft }, badge: { fontFamily: theme.type.body, color: theme.colors.accent, fontSize: 10 },
  forecastValue: { fontFamily: theme.type.heading, fontSize: 32, color: theme.colors.accent },
});
