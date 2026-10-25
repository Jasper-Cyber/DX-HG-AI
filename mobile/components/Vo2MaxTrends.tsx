import { ChartLegend } from "./ChartLegend";
import { SelectableChartPoint } from "./SelectableChartPoint";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Line, Text as SvgText } from "react-native-svg";
import type { Reading } from "@/api/types";
import { dailyMetricHistory, healthTrends } from "@/utils/healthTrends";
import { theme, metricPalette, chartSeries } from "@/theme";
import { Icon } from "./Icon";
const palette = metricPalette.vo2max;
const DOT = chartSeries.daily;
export function Vo2MaxTrends({ readings }: { readings: Reading[] }) {
  const [showMethod, setShowMethod] = useState(false);
  const [days, setDays] = useState<28 | 90>(28);
  const [selected, setSelected] = useState<string | null>(null);
  const points = useMemo(() => dailyMetricHistory(readings, "vo2max", days, false), [readings, days]);
  const comparison = useMemo(() => healthTrends(readings, "vo2max"), [readings]);
  const valid = points.filter(d => d.mean !== null);
  const chosen = valid.find(d => d.date === selected) ?? valid[valid.length - 1];
  const selectedIndex = chosen ? valid.indexOf(chosen) : -1;
  const values = valid.map(d => d.mean!);
  const low = values.length ? Math.floor(Math.min(...values) - 1) : 0;
  const high = values.length ? Math.ceil(Math.max(...values) + 1) : 1;
  const x = (i: number) => 35 + i / Math.max(points.length - 1, 1) * 270;
  const y = (v: number) => 150 - (v - low) / (high - low) * 120;
  const change = comparison?.change;
  const comparable = change !== null && change !== undefined;
  return <View style={s.card}>
    <View style={s.heading}><Icon name="activity" color={DOT} /><Text style={s.title}>VO₂ Max Trends</Text></View>
    <Text style={s.description}>Cardio-fitness trend · mL/kg/min</Text>
    <Text style={s.notice}>Daily synthetic demo values · not a fitness assessment.</Text>
    <View style={s.tabs}>{([28, 90] as const).map(n => <Pressable key={n} onPress={() => { setDays(n); setSelected(null); }} accessibilityRole="button" accessibilityState={{ selected: days === n }} style={[s.tab, days === n && { backgroundColor: palette.ink }]}><Text style={[s.tabText, days === n && { color: theme.colors.onAccent }]}>{n} days</Text></Pressable>)}</View>
    {valid.length ? <>
      <View style={s.difference}><Text style={s.description}>Trend difference</Text><Text style={s.delta}>{comparable ? `${change! > 0 ? "+" : ""}${change!.toFixed(1)}` : "—"} <Text style={s.unit}>mL/kg/min</Text></Text><Text style={s.small}>Latest 7 complete days vs previous 7 days</Text></View>
      {comparable && <View style={s.comparison}><View><Text style={s.small}>Previous week</Text><Text style={[s.number, { color: chartSeries.previous }]}>{comparison!.previousAverage!.toFixed(1)}</Text></View><Text style={s.number}>→</Text><View><Text style={s.small}>Latest week</Text><Text style={[s.number, { color: chartSeries.current }]}>{comparison!.average!.toFixed(1)}</Text></View></View>}
      <Svg width="100%" height={194} viewBox="0 0 320 194" accessibilityLabel="VO2 max daily scatter plot with weekly comparison lines">
        {[0, 1, 2, 3, 4].map(i => { const value = low + (high - low) * i / 4; return <Line key={i} x1={35} x2={310} y1={y(value)} y2={y(value)} stroke={theme.colors.border} />; })}
        {[0, 1, 2, 3, 4].map(i => { const value = low + (high - low) * i / 4; return <SvgText key={i} x={29} y={y(value) + 3} textAnchor="end" fontSize={12} fill={theme.colors.textSecondary}>{value.toFixed(1)}</SvgText>; })}
        {comparable && <><Line x1={x(days - 14)} x2={x(days - 8)} y1={y(comparison!.previousAverage!)} y2={y(comparison!.previousAverage!)} stroke={chartSeries.previous} strokeDasharray="4 3" strokeWidth={2} /><Line x1={x(days - 7)} x2={x(days - 1)} y1={y(comparison!.average!)} y2={y(comparison!.average!)} stroke={chartSeries.current} strokeWidth={2} /></>}
        {points.map((d, i) => d.mean === null ? null : <SelectableChartPoint key={d.date} cx={x(i)} cy={y(d.mean)} r={d.date === chosen?.date ? 5 : 3.5} fill={DOT} stroke={d.date === chosen?.date ? theme.colors.textPrimary : DOT} label={`VO₂ max for ${d.date}: ${d.mean.toFixed(1)} mL/kg/min`} selected={d.date === chosen?.date} onSelect={() => setSelected(d.date)} />)}
        {[0, Math.floor((days - 1) / 2), days - 1].map(i => <SvgText key={i} x={x(i)} y={177} textAnchor={i === days - 1 ? "end" : "start"} fontSize={12} fill={theme.colors.textSecondary}>{points[i]?.date.slice(5)}</SvgText>)}
      </Svg>
      <ChartLegend items={[{ label: "Daily value", color: DOT, mark: "dot" }, ...(comparable ? [{ label: "Previous week mean", color: chartSeries.previous, mark: "dash" as const }, { label: "Latest week mean", color: chartSeries.current }] : [])]} />
      <View style={s.selected}><Text style={s.description}>{chosen?.date}</Text><Text style={s.number}>{chosen?.mean?.toFixed(1)} <Text style={s.unit}>mL/kg/min</Text></Text></View>
      <View style={s.navigation}><Pressable accessibilityRole="button" disabled={selectedIndex <= 0} accessibilityState={{ disabled: selectedIndex <= 0 }} onPress={() => setSelected(valid[selectedIndex - 1].date)} style={[s.navButton, selectedIndex <= 0 && { opacity: .4 }]}><Text style={s.navText}>← Earlier reading</Text></Pressable><Pressable accessibilityRole="button" disabled={selectedIndex >= valid.length - 1} accessibilityState={{ disabled: selectedIndex >= valid.length - 1 }} onPress={() => setSelected(valid[selectedIndex + 1].date)} style={[s.navButton, selectedIndex >= valid.length - 1 && { opacity: .4 }]}><Text style={s.navText}>Later reading →</Text></Pressable></View>
      {!comparable && <Text style={s.small}>A comparison needs at least 5 usable daily entries in each seven-day period.</Text>}
      <Pressable accessibilityRole="button" accessibilityState={{ expanded: showMethod }} onPress={() => setShowMethod(!showMethod)} style={({ pressed }) => [s.methodButton, pressed && { backgroundColor: palette.soft }]}><Text style={s.methodLabel}>{showMethod ? "Hide data notes −" : "About this data +"}</Text></Pressable>
      {showMethod && <Text style={s.small}>{valid.length} usable daily entries. Values are synthetic, not measured or calculated from your heart rate or blood oxygen. The current partial simulation day is excluded. Missing days have no dots.</Text>}
    </> : <Text style={s.description}>No daily VO₂ max history yet. Start the simulator to generate synthetic readings.</Text>}
  </View>;
}
const s = StyleSheet.create({
  methodButton: { minHeight: 48, justifyContent: "center", paddingHorizontal: 12, borderRadius: 10, borderWidth: 1, borderColor: theme.colors.controlBorder },
  methodLabel: { fontFamily: theme.type.heading, fontSize: 13, color: theme.colors.textPrimary },
  card: { backgroundColor: theme.colors.surface, borderRadius: 24, padding: 20, borderWidth: 1, borderColor: theme.colors.border, gap: 12, marginVertical: 8 },
  heading: { flexDirection: "row", alignItems: "center", gap: 8 }, title: { fontFamily: theme.type.heading, fontSize: 22, color: theme.colors.textPrimary },
  description: { fontFamily: theme.type.body, fontSize: 13, lineHeight: 20, color: theme.colors.textSecondary },
  notice: { fontFamily: theme.type.body, fontSize: 12, lineHeight: 17, color: theme.colors.textSecondary },
  tabs: { flexDirection: "row", padding: 4, gap: 4, backgroundColor: palette.soft, borderRadius: 12 }, tab: { minHeight: 48, justifyContent: "center", flex: 1, alignItems: "center", padding: 10, borderRadius: 9 }, tabText: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textPrimary },
  difference: { backgroundColor: palette.soft, padding: 15, borderRadius: 12, gap: 5 }, delta: { fontFamily: theme.type.heading, fontSize: 30, color: palette.ink },
  unit: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary }, small: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary, lineHeight: 18 },
  comparison: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 10 }, number: { fontFamily: theme.type.heading, fontSize: 23, color: theme.colors.textPrimary },
  legend: { flexDirection: "row", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }, selected: { padding: 12, backgroundColor: theme.colors.inset, borderRadius: 10, gap: 4 },
  navigation: { flexDirection: "row", justifyContent: "space-between", gap: 8 }, navButton: { borderWidth: 1, borderColor: palette.ink, flex: 1, minHeight: 44, justifyContent: "center", alignItems: "center", backgroundColor: palette.soft, borderRadius: 8 }, navText: { fontFamily: theme.type.body, color: palette.ink, fontSize: 11 },
});
