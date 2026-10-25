import { LineChart } from "react-native-gifted-charts";

import { theme } from "@/theme";

interface MiniTrendProps {
  /** Values oldest→newest; null entries are treated as gaps. */
  values: (number | null)[];
  color: string;
  height?: number;
}

/**
 * Compact sparkline-style trend for a metric card. Intentionally chromeless
 * (no axes/labels) so it reads as a glanceable mini chart on the dashboard.
 */
export function MiniTrend({ values, color, height = 40 }: MiniTrendProps) {
  // gifted-charts needs finite numbers; drop leading/trailing nulls and
  // substitute interior nulls with the previous known value so the line stays
  // continuous rather than crashing on NaN.
  const data = toChartData(values);
  if (data.length < 2) return null;

  return (
    <LineChart
      data={data}
      height={height}
      thickness={2}
      color={color}
      hideDataPoints
      hideAxesAndRules
      hideYAxisText
      yAxisThickness={0}
      xAxisThickness={0}
      initialSpacing={0}
      endSpacing={0}
      adjustToWidth
      disableScroll
      areaChart
      startFillColor={color}
      endFillColor={theme.colors.surface}
      startOpacity={0.25}
      endOpacity={0}
    />
  );
}

/** Map a nullable numeric series to gifted-charts points, bridging gaps. */
export function toChartData(values: (number | null)[]): { value: number }[] {
  const points: { value: number }[] = [];
  let last: number | null = null;
  for (const v of values) {
    const resolved: number | null = v ?? last;
    if (resolved === null || Number.isNaN(resolved)) continue;
    points.push({ value: resolved });
    last = resolved;
  }
  return points;
}
