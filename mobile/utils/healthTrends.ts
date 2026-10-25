import type { MetricType, Reading } from "@/api/types";
import { hasUsableValue } from "./metrics";

const DAY = 86_400_000;
export interface DailySummary {
  date: string;
  mean: number | null;
  min: number | null;
  max: number | null;
  count: number;
}
const mean = (values: number[]) => values.length ? values.reduce((sum, v) => sum + v, 0) / values.length : null;

/** Equal UTC calendar windows ending before the current (incomplete) simulation day. */
export function healthTrends(readings: Reading[], metric: MetricType, days: 7 | 30 = 7) {
  const timestamps = readings.map(r => Date.parse(r.timestamp)).filter(Number.isFinite);
  if (!timestamps.length) return null;
  const today = Math.floor(Math.max(...timestamps) / DAY) * DAY;
  const buckets = new Map<number, number[]>();
  for (const r of readings) {
    if (r.metricType !== metric || !hasUsableValue(r)) continue;
    const day = Math.floor(Date.parse(r.timestamp) / DAY) * DAY;
    if (!Number.isFinite(day) || day >= today || day < today - 2 * days * DAY) continue;
    const bucket = buckets.get(day) ?? [];
    bucket.push(r.value!);
    buckets.set(day, bucket);
  }
  const summarize = (start: number, length: number): DailySummary[] => Array.from({ length }, (_, i) => {
    const time = start + i * DAY;
    const values = buckets.get(time) ?? [];
    return { date: new Date(time).toISOString().slice(0, 10), mean: mean(values),
      min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null, count: values.length };
  });
  const current = summarize(today - days * DAY, days);
  const previous = summarize(today - 2 * days * DAY, days);
  // Every calendar day must have at least half of its expected hourly samples.
  // This prevents a sparse day from masquerading as a comparable full period.
  const minimumSamples = metric === "vo2max" ? 1 : 12;
  const comparable = metric === "vo2max"
    ? [current, previous].every(period => period.filter(d => d.count >= 1).length >= Math.ceil(days * 0.7))
    : [...current, ...previous].every(d => d.count >= minimumSamples);
  const weightedMean = (rows: DailySummary[]) => {
    const count = rows.reduce((sum, d) => sum + d.count, 0);
    return count ? rows.reduce((sum, d) => sum + (d.mean ?? 0) * d.count, 0) / count : null;
  };
  const average = weightedMean(current);
  const previousAverage = weightedMean(previous);
  const change = comparable && average !== null && previousAverage !== null ? average - previousAverage : null;
  const percentChange = change !== null && previousAverage !== null && previousAverage !== 0 ? change / Math.abs(previousAverage) * 100 : null;

  // An illustrative one-day extrapolation, never a disease/risk prediction.
  // Fit on recent daily means with >=12 usable hourly samples, retaining actual day spacing.
  const recent = summarize(today - 7 * DAY, 7);
  const fit = recent.map((d, x) => ({ ...d, x })).filter(d => d.mean !== null && d.count >= 12);
  let forecast: { value: number; date: string; daysUsed: number } | null = null;
  if (["hr", "hrv", "spo2"].includes(metric) && fit.length >= 4 && recent[6].count >= 12) {
    const xMean = fit.reduce((sum, d) => sum + d.x, 0) / fit.length;
    const yMean = fit.reduce((sum, d) => sum + d.mean!, 0) / fit.length;
    const variance = fit.reduce((sum, d) => sum + (d.x - xMean) ** 2, 0);
    const slope = fit.reduce((sum, d) => sum + (d.x - xMean) * (d.mean! - yMean), 0) / variance;
    const value = yMean + slope * (7 - xMean);
    // Suppress impossible extrapolations instead of clipping them into plausible-looking values.
    if (Number.isFinite(value) && value >= 0 && (metric !== "spo2" || value <= 100)) {
      forecast = { value, date: new Date(today).toISOString().slice(0, 10), daysUsed: fit.length };
    }
  }
  return { current, previous, average, previousAverage, change, percentChange, forecast,
    sampleCount: current.reduce((sum, d) => sum + d.count, 0),
    yesterday: current[current.length - 1], excludedPartialDate: new Date(today).toISOString().slice(0, 10) };
}

/** Calendar buckets preserve empty days, including an explicitly partial current day. */
export function dailyMetricHistory(readings: Reading[], metric: MetricType, days: number, includeToday = true): DailySummary[] {
  const timestamps = readings.map(r => Date.parse(r.timestamp)).filter(Number.isFinite);
  if (!timestamps.length) return [];
  const today = Math.floor(Math.max(...timestamps) / DAY) * DAY;
  const end = includeToday ? today : today - DAY;
  const start = end - (days - 1) * DAY;
  const buckets = new Map<number, number[]>();
  for (const r of readings) {
    if (r.metricType !== metric || !hasUsableValue(r)) continue;
    const day = Math.floor(Date.parse(r.timestamp) / DAY) * DAY;
    if (day < start || day > end || !Number.isFinite(day)) continue;
    const values = buckets.get(day) ?? [];
    values.push(r.value!);
    buckets.set(day, values);
  }
  return Array.from({ length: days }, (_, i) => {
    const time = start + i * DAY;
    const values = buckets.get(time) ?? [];
    return { date: new Date(time).toISOString().slice(0, 10), mean: mean(values),
      min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null, count: values.length };
  });
}
