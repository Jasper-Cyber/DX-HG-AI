/**
 * Chart data transforms for the History screen. Pure + testable (Task 27).
 */
import type { TrendPoint, TrendSeries } from "@/api/types";

export interface ChartPoint {
  value: number;
  /** Short x-axis label (derived from the period). */
  label?: string;
  /** Marks a point flagged as anomalous so the chart can emphasize it. */
  anomaly?: boolean;
}

/**
 * Convert a trend series into gifted-charts points, using each period's mean.
 * Missing means (null) are bridged from the previous known value so the line
 * stays continuous; a point with no prior value is skipped. Optionally thins
 * labels to avoid clutter.
 */
export function toTrendChartData(
  points: TrendPoint[],
  options: { labelEvery?: number; anomalyPeriods?: Set<string> } = {},
): ChartPoint[] {
  const { labelEvery = 0, anomalyPeriods } = options;
  const out: ChartPoint[] = [];
  let last: number | null = null;

  points.forEach((p, i) => {
    const resolved: number | null = p.mean ?? last;
    if (resolved === null || Number.isNaN(resolved)) return;
    last = resolved;

    const point: ChartPoint = { value: resolved };
    if (labelEvery > 0 && i % labelEvery === 0) point.label = shortLabel(p.period);
    if (anomalyPeriods?.has(p.period)) point.anomaly = true;
    out.push(point);
  });

  return out;
}

/**
 * A compact axis label (month/day) from a period string. Uses UTC getters so
 * the label is deterministic regardless of the device's timezone. Falls back
 * to the raw period when it is not a parseable date.
 */
export function shortLabel(period: string): string {
  const d = new Date(period);
  if (Number.isNaN(d.getTime())) return period;
  return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
}

/** Min/max across a series' period means, for chart scaling. Null when empty. */
export function seriesRange(series: TrendSeries): { min: number; max: number } | null {
  const values = series.points
    .map((p) => p.mean)
    .filter((v): v is number => v !== null && !Number.isNaN(v));
  if (values.length === 0) return null;
  return { min: Math.min(...values), max: Math.max(...values) };
}

/** Whether a series has at least one usable data point. */
export function seriesHasData(series: TrendSeries): boolean {
  return series.points.some((p) => p.mean !== null && !Number.isNaN(p.mean));
}
