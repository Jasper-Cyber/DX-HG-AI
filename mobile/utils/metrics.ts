/**
 * Metric formatting + derivation helpers for the mobile UI.
 *
 * Pure functions, no React — kept separate so screens stay thin and the logic
 * is unit-testable (Task 27).
 */
import type { MetricType, Quality, Reading } from "@/api/types";

/** Display metadata per metric: label and unit. Metric colors live in the shared theme. */
export const METRIC_META: Record<
  MetricType,
  { label: string; unit: string }
> = {
  vo2max: { label: "VO₂ max", unit: "mL/kg/min" },
  hr: { label: "Heart Rate", unit: "bpm" },
  hrv: { label: "HRV", unit: "ms" },
  spo2: { label: "Blood Oxygen", unit: "%" },
  rhythm: { label: "Rhythm", unit: "" },
  activity: { label: "Activity", unit: "steps" },
  sleep: { label: "Sleep", unit: "h" },
};

/** The four metrics shown as primary cards on the dashboard, in order. */
export const PRIMARY_METRICS: MetricType[] = ["hr", "hrv", "spo2", "rhythm"];

/** Secondary daily indicators. */
export const SECONDARY_METRICS: MetricType[] = ["activity", "sleep"];

/**
 * Format a reading's value for display. Returns a dash for missing/low-quality
 * samples so the UI never shows a misleading number (Req 1.6).
 */
export function formatMetricValue(value: number | null, metric: MetricType): string {
  if (value === null || Number.isNaN(value)) return "—";

  switch (metric) {
    case "rhythm":
      // rhythm is encoded numerically: 0 => regular, anything else => irregular.
      return value === 0 ? "Regular" : "Irregular";
    case "spo2":
      return `${Math.round(value)}`;
    case "hrv":
    case "hr":
    case "activity":
      return `${Math.round(value)}`;
    case "vo2max":
    case "sleep":
      return value.toFixed(1);
    default:
      return `${value}`;
  }
}

/** Human-readable label for a reading's data quality. */
export function qualityLabel(quality: Quality): string {
  switch (quality) {
    case "ok":
      return "";
    case "low":
      return "Low quality";
    case "missing":
      return "No data";
    default:
      return "";
  }
}

/**
 * Pick the most recent reading for a metric from a flat list of readings.
 * Returns undefined when there is no reading for that metric.
 */
export function latestForMetric(
  readings: Reading[] | undefined,
  metric: MetricType,
): Reading | undefined {
  if (!readings || readings.length === 0) return undefined;
  let latest: Reading | undefined;
  for (const r of readings) {
    if (r.metricType !== metric) continue;
    if (!latest || r.timestamp > latest.timestamp) latest = r;
  }
  return latest;
}

/**
 * Build a compact numeric series (oldest→newest) for a metric, for mini trend
 * charts. Missing/low values become null so charts can show gaps.
 */
export function miniSeriesForMetric(
  readings: Reading[] | undefined,
  metric: MetricType,
  limit = 20,
): (number | null)[] {
  if (!readings) return [];
  const forMetric = readings
    .filter((r) => r.metricType === metric)
    .sort((a, b) => (a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0));
  const tail = forMetric.slice(-limit);
  return tail.map((r) => hasUsableValue(r) ? r.value : null);
}

/** Whether a reading represents usable data (not missing/low). */
export function hasUsableValue(reading: Reading | undefined): boolean {
  return !!reading && reading.value !== null && Number.isFinite(reading.value) && reading.quality === "ok";
}

/** A trailing window on the simulation's clock, not the device's real date. */
export function readingsInWindow(readings: Reading[], hours: number | null): Reading[] {
  const dated = readings.filter(r => Number.isFinite(Date.parse(r.timestamp)));
  if (hours === null || !dated.length) return dated;
  const end = Math.max(...dated.map(r => Date.parse(r.timestamp)));
  return dated.filter(r => Date.parse(r.timestamp) > end - hours * 3_600_000);
}

/** Descriptive statistics exclude missing, low-quality, and non-finite samples. */
export function summarizeMetric(readings: Reading[], metric: MetricType) {
  const rows = readings.filter(r => r.metricType === metric)
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const valid = rows.filter(hasUsableValue);
  const values = valid.map(r => r.value!);
  return {
    rows, validCount: valid.length, totalCount: rows.length,
    min: values.length ? Math.min(...values) : null,
    max: values.length ? Math.max(...values) : null,
    mean: values.length ? values.reduce((sum, v) => sum + v, 0) / values.length : null,
    flagged: metric === "rhythm" ? values.filter(v => v !== 0).length : 0,
    first: rows[0]?.timestamp,
    last: rows[rows.length - 1]?.timestamp,
  };
}

export function formatSampleTime(timestamp?: string): string {
  if (!timestamp || !Number.isFinite(Date.parse(timestamp))) return "No timestamp";
  const date = new Date(timestamp);
  return `${date.toISOString().slice(0, 10)} · ${date.toISOString().slice(11, 16)} UTC`;
}
