import { ChartLegend } from "./ChartLegend";
import { useId } from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop } from "react-native-svg";
import type { TrendSeries } from "@/api/types";
import { METRIC_META } from "@/utils/metrics";
import { theme, metricPalette, chartCompanion } from "@/theme";
import { Icon } from "./Icon";

export function TrendChart({ series, anomalyPeriods }: { series: TrendSeries; anomalyPeriods?: Set<string> }) {
  const id = "history" + useId().replace(/:/g, "");
  const meta = METRIC_META[series.metric];
  const palette = metricPalette[series.metric];
  const valid = series.points.filter(p => p.mean !== null && Number.isFinite(p.mean));
  const baseline = series.baselineMean;
  const count = valid.reduce((sum, p) => sum + p.count, 0);
  const average = count ? valid.reduce((sum, p) => sum + p.mean! * p.count, 0) / count : null;
  const minima = valid.flatMap(p => p.min !== null && Number.isFinite(p.min) ? [p.min] : []);
  const maxima = valid.flatMap(p => p.max !== null && Number.isFinite(p.max) ? [p.max] : []);
  const minimum = minima.length ? Math.min(...minima) : null;
  const maximum = maxima.length ? Math.max(...maxima) : null;
  const values = valid.map(p => p.mean!);
  if (baseline !== null) values.push(baseline);
  const low = Math.min(...values), high = Math.max(...values), span = Math.max(high - low, 1);
  const y = (v: number) => 110 - (v - low) / span * 86;
  const x = (i: number) => 6 + i / Math.max(series.points.length - 1, 1) * 288;
  // Break the trace at missing periods instead of fabricating readings.
  let drawing = false;
  const path = series.points.map((p, i) => {
    if (p.mean === null || !Number.isFinite(p.mean)) { drawing = false; return ""; }
    const segment = `${drawing ? "L" : "M"}${x(i)},${y(p.mean)}`;
    drawing = true;
    return segment;
  }).join(" ");
  const first = valid[0], last = valid[valid.length - 1];
  const date = (value: string) => value.slice(5, 10).replace("-", "/");
  return <View style={[s.card, { borderTopWidth: 3, borderTopColor: palette.ink }]}>
    <View style={s.header}><View style={[s.icon, { backgroundColor: palette.soft }]}><Icon name={series.metric === "hr" ? "heart" : series.metric === "spo2" ? "drop" : "pulse"} size={18} color={palette.ink} /></View><View style={{ flex: 1 }}><Text style={s.title}>{meta.label}</Text><Text style={s.subtitle}>Period averages</Text></View>{baseline !== null && <Text style={[s.baseline, { color: theme.colors.textSecondary }]}>Baseline {baseline.toFixed(1)}</Text>}</View>
    {average === null ? <Text style={s.empty}>No data for this range.</Text> : <>
      <View style={s.valueRow}><Text style={[s.value, { color: palette.ink }]}>{average.toFixed(series.metric === "spo2" ? 1 : 0)}</Text><Text style={s.unit}>AVG {meta.unit.toUpperCase()}</Text></View>
      <View style={s.summary}><Text style={s.summaryText}>Minimum <Text style={s.strong}>{minimum?.toFixed(1) ?? "—"}</Text></Text><Text style={s.summaryText}>Maximum <Text style={s.strong}>{maximum?.toFixed(1) ?? "—"}</Text></Text></View>
      <View style={s.plot}>
        <View style={s.dates}><Text style={s.axis}>Chart scale: {low.toFixed(1)}–{high.toFixed(1)} {meta.unit}</Text></View>
        <Svg width="100%" height={135} viewBox="0 0 300 135" preserveAspectRatio="none">
          <Defs><LinearGradient id={id} x1="0" y1="0" x2="0" y2="1"><Stop offset="0" stopColor={palette.ink} stopOpacity={.2} /><Stop offset="1" stopColor={palette.ink} stopOpacity={0} /></LinearGradient></Defs>
          {[25, 68, 110].map(v => <Line key={v} x1={0} x2={300} y1={v} y2={v} stroke={theme.colors.border} strokeDasharray="2 5" strokeWidth={.6} />)}
          {valid.length === series.points.length && <Path d={`${path} L294,135 L6,135 Z`} fill={`url(#${id})`} />}
          {baseline !== null && <Line x1={0} x2={300} y1={y(baseline)} y2={y(baseline)} stroke={chartCompanion[series.metric]} strokeDasharray="4 4" strokeWidth={2} />}
          <Path d={path} fill="none" stroke={palette.ink} strokeWidth={1.8} vectorEffect="non-scaling-stroke" />
          {series.points.map((p, i) => p.mean !== null && Number.isFinite(p.mean) && (i === series.points.length - 1 || anomalyPeriods?.has(p.period)) ? <Circle key={p.period} cx={x(i)} cy={y(p.mean)} r={2.8} fill={anomalyPeriods?.has(p.period) ? theme.colors.warn : palette.ink} /> : null)}
        </Svg>
        <View style={s.dates}><Text style={s.axis}>{date(first.period)}</Text><Text style={s.axis}>{date(last.period)}</Text></View>
      </View>
      <ChartLegend items={[{ label: "Period average", color: palette.ink }, ...(baseline !== null ? [{ label: "Learned baseline", color: chartCompanion[series.metric], mark: "dash" as const }] : []), ...(anomalyPeriods?.size ? [{ label: "Flagged period", color: theme.colors.warn, mark: "dot" as const }] : [])]} />
      <Text style={s.axis}>{count} usable samples · UTC dates</Text>
      {baseline !== null && <Text style={s.axis}>Dashed line: learned baseline. Gaps mark unavailable data.</Text>}
    </>}
  </View>;
}
const s = StyleSheet.create({
  summary: { flexDirection: "row", justifyContent: "space-between", flexWrap: "wrap", gap: 8 },
  summaryText: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 13 },
  strong: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 18 },
  card: { backgroundColor: theme.colors.surface, borderRadius: 17, borderWidth: 1, borderColor: theme.colors.border, padding: 17, gap: 12 },
  header: { flexDirection: "row", alignItems: "center", gap: 9 }, icon: { backgroundColor: theme.colors.surfaceAlt, borderRadius: 8, padding: 7 },
  title: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 17 },
  subtitle: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: 12, marginTop: 3 },
  baseline: { color: theme.colors.pale, fontFamily: theme.type.mono, fontSize: 12, backgroundColor: theme.colors.inset, padding: 6, borderRadius: 6 },
  valueRow: { flexDirection: "row", justifyContent: "flex-end", alignItems: "baseline", gap: 6 }, value: { fontFamily: theme.type.heading, fontSize: 30, color: theme.colors.textPrimary },
  unit: { fontFamily: theme.type.mono, fontSize: 12, color: theme.colors.textSecondary },
  plot: { backgroundColor: theme.colors.inset, borderRadius: 10, padding: 10 },
  dates: { flexDirection: "row", justifyContent: "space-between", paddingTop: 6 },
  axis: { fontFamily: theme.type.mono, fontSize: 12, color: theme.colors.textSecondary },
  empty: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary, paddingVertical: 20 },
});
