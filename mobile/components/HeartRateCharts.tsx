import { ChartLegend } from "./ChartLegend";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Line, Path, Text as SvgText } from "react-native-svg";
import type { Reading } from "@/api/types";
import { dailyMetricHistory } from "@/utils/healthTrends";
import { hasUsableValue } from "@/utils/metrics";
import { theme, metricPalette, chartSeries } from "@/theme";
import { Icon } from "./Icon";
const SERIES = [
  { key: "min" as const, name: "Minimum", color: chartSeries.minimum },
  { key: "mean" as const, name: "Average", color: chartSeries.average },
  { key: "max" as const, name: "Maximum", color: chartSeries.maximum },
];
function scale(values: number[]) {
  const low = values.length ? Math.max(0, Math.floor((Math.min(...values) - 5) / 10) * 10) : 40;
  const high = values.length ? Math.max(low + 20, Math.ceil((Math.max(...values) + 5) / 10) * 10) : 100;
  return { low, high, y: (v: number) => 148 - (v - low) / (high - low) * 120 };
}
function Grid({ low, high, y }: ReturnType<typeof scale>) {
  return <>{[0, 1, 2, 3].map(i => {
    const value = low + (high - low) * i / 3;
    return <ViewlessGrid key={i} value={value} y={y(value)} />;
  })}</>;
}
function ViewlessGrid({ value, y }: { value: number; y: number }) {
  return <><Line x1={35} x2={310} y1={y} y2={y} stroke={theme.colors.border} /><SvgText x={29} y={y + 3} textAnchor="end" fontSize={12} fill={theme.colors.textSecondary}>{value.toFixed(0)}</SvgText></>;
}
export function HeartRateCharts({ readings, compact = false }: { readings: Reading[]; compact?: boolean }) {
  const [view, setView] = useState<"today" | "week">("week");
  const days = useMemo(() => dailyMetricHistory(readings, "hr", 7), [readings]);
  const [selected, setSelected] = useState<string | null>(null);
  if (!days.length) return <Text style={s.muted}>Heart-rate trends will appear when the simulator has readings.</Text>;
  const today = days[6];
  const selectedDay = days.find(d => d.date === selected) ?? today;
  const todayRows = readings.filter(r => r.metricType === "hr" && Number.isFinite(Date.parse(r.timestamp)) && new Date(r.timestamp).toISOString().slice(0, 10) === today.date).sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const validToday = todayRows.filter(hasUsableValue);
  const todayScale = scale(validToday.map(r => r.value!));
  const weekScale = scale(days.flatMap(d => d.min === null || d.max === null ? [] : [d.min, d.max]));
  const dayStart = Date.parse(today.date + "T00:00:00Z");
  const xTime = (time: string) => 35 + (Date.parse(time) - dayStart) / 86_400_000 * 275;
  let drawing = false;
  let previousTime: number | null = null;
  const path = todayRows.map(r => {
    if (!hasUsableValue(r)) { drawing = false; return ""; }
    const time = Date.parse(r.timestamp);
    if (previousTime !== null && time - previousTime > 3_600_000) drawing = false;
    const result = `${drawing ? "L" : "M"}${xTime(r.timestamp)},${todayScale.y(r.value!)}`;
    drawing = true; previousTime = time;
    return result;
  }).join(" ");
  const fmt = (v: number | null) => v === null ? "—" : v.toFixed(1);
  return <View style={s.stack}>
    {compact && <View style={s.tabs}>{(["today", "week"] as const).map(key => <Pressable key={key} accessibilityRole="button" accessibilityLabel={key === "today" ? "Show today’s heart rate" : "Show 7-day heart rate range"} accessibilityState={{ selected: view === key }} onPress={() => setView(key)} style={({ pressed }) => [s.tab, view === key && { backgroundColor: metricPalette.hr.ink }, pressed && { opacity: .8 }]}><Text style={[s.tabText, view === key && { color: theme.colors.onAccent }]}>{key === "today" ? "Today" : "7-day range"}</Text></Pressable>)}</View>}
    {(!compact || view === "today") && <View style={s.panel}>
      <View style={s.heading}><Icon name="heart" color={metricPalette.hr.ink} /><Text style={s.title}>Heart Rate Today</Text><Text style={s.unit}>bpm</Text></View>
      <Text style={s.muted}>{today.date} · simulation day · partial</Text>
      {validToday.length ? <Svg width="100%" height={185} viewBox="0 0 320 185" accessibilityLabel="Hourly heart rate today with time and bpm axes">
        <Grid {...todayScale} />
        {[0, 6, 12, 18, 24].map(hour => <SvgText key={hour} x={35 + hour / 24 * 275} y={172} textAnchor={hour === 24 ? "end" : "middle"} fontSize={12} fill={theme.colors.textSecondary}>{`${hour.toString().padStart(2, "0")}:00`}</SvgText>)}
        <Path d={path} stroke={chartSeries.average} strokeWidth={2} fill="none" />
        {validToday.map(r => <Circle key={r.timestamp} cx={xTime(r.timestamp)} cy={todayScale.y(r.value!)} r={3} fill={chartSeries.maximum} stroke={theme.colors.surface} strokeWidth={1} />)}
      </Svg> : <Text style={s.muted}>No usable heart-rate samples today.</Text>}
      {validToday.length > 0 && <ChartLegend items={[{ label: "Hourly trace", color: chartSeries.average }, { label: "Recorded sample", color: chartSeries.maximum, mark: "dot" }]} />}
      <View style={s.stats}>{SERIES.map(item => <View key={item.key}><Text style={[s.small, { color: item.color }]}>{item.name}</Text><Text style={[s.value, { color: item.color }]}>{fmt(today[item.key])}</Text></View>)}</View>
      <Text style={s.small}>{today.count} usable hourly samples · UTC · gaps are not interpolated</Text>
    </View>}
    {(!compact || view === "week") && <View style={s.panel}>
      <View style={s.heading}><Icon name="heart" color={metricPalette.hr.ink} /><Text style={s.title}>Preceding 7 Days HR</Text></View>
      <Text style={s.muted}>Daily minimum, average & maximum · bpm</Text>
      <Svg width="100%" height={174} viewBox="0 0 320 174" accessibilityLabel="Seven-day heart-rate minimum, average and maximum markers">
        <Grid {...weekScale} />
        {days.map((d, i) => <Line key={d.date} x1={52 + i * 40} x2={52 + i * 40} y1={20} y2={151} stroke={d.date === selectedDay.date ? metricPalette.hr.soft : "transparent"} strokeWidth={30} />)}
        {days.flatMap((d, i) => SERIES.map(item => d[item.key] === null ? null : <Line key={`${d.date}-${item.key}`} x1={42 + i * 40} x2={62 + i * 40} y1={weekScale.y(d[item.key]!)} y2={weekScale.y(d[item.key]!)} stroke={item.color} strokeWidth={5} strokeLinecap="round" />))}
      </Svg>
      <View style={s.days}>{days.map((d, i) => <Pressable key={d.date} onPress={() => setSelected(d.date)} accessibilityRole="button" accessibilityLabel={`Heart rate for ${d.date}`} accessibilityState={{ selected: d.date === selectedDay.date }} style={[s.day, d.date === selectedDay.date && { backgroundColor: metricPalette.hr.ink }]}><Text style={[s.dayText, d.date === selectedDay.date && { color: theme.colors.onAccent }]}>{i === 6 ? "Today" : new Date(d.date + "T00:00:00Z").toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" })}</Text><Text style={[s.dayText, d.date === selectedDay.date && { color: theme.colors.onAccent }]}>{d.date.slice(8)}</Text></Pressable>)}</View>
      <View style={s.legend}>{SERIES.map(item => <View key={item.key} style={s.legendItem}><View style={[s.swatch, { backgroundColor: item.color }]} /><Text style={s.small}>{item.name}</Text></View>)}</View>
      <Text style={s.muted}>{selectedDay.date}{selectedDay.date === today.date ? " · partial day" : ""}</Text>
      <View style={s.stats}>{SERIES.map(item => <View key={item.key}><Text style={s.small}>{item.name}</Text><Text style={[s.value, { color: item.color }]}>{fmt(selectedDay[item.key])}</Text></View>)}</View>
      <Text style={s.small}>{selectedDay.count} usable samples. Empty days have no markers.</Text>
    </View>}
  </View>;
}
const s = StyleSheet.create({
  tabs: { flexDirection: "row", padding: 4, gap: 4, backgroundColor: theme.colors.surfaceAlt, borderRadius: 14 },
  tab: { flex: 1, minHeight: 48, justifyContent: "center", alignItems: "center", borderRadius: 10 },
  tabText: { fontFamily: theme.type.heading, fontSize: 14, color: theme.colors.textPrimary },
  stack: { gap: 14 }, panel: { backgroundColor: theme.colors.surface, borderWidth: 1, borderColor: theme.colors.border, borderRadius: 24, padding: 16, gap: 10 },
  heading: { flexDirection: "row", alignItems: "center", gap: 8 }, title: { fontFamily: theme.type.heading, fontSize: 18, color: theme.colors.textPrimary, flex: 1 },
  unit: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary },
  muted: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary, lineHeight: 19 },
  small: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary, lineHeight: 17 },
  stats: { flexDirection: "row", justifyContent: "space-between", gap: 6 }, value: { fontFamily: theme.type.heading, fontSize: 22, color: theme.colors.textPrimary, marginTop: 3 },
  days: { flexDirection: "row", gap: 2, marginLeft: 16 }, day: { flex: 1, minHeight: 44, alignItems: "center", justifyContent: "center", borderRadius: 7 },
  dayText: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textPrimary },
  legend: { flexDirection: "row", flexWrap: "wrap", gap: 12, borderTopWidth: 1, borderColor: theme.colors.border, paddingTop: 12 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 }, swatch: { width: 15, height: 5, borderRadius: 3 },
});
