import { StyleSheet, Text, View } from "react-native";
import { LineChart } from "react-native-gifted-charts";

import type { TrendSeries } from "@/api/types";
import { METRIC_META } from "@/utils/metrics";
import { seriesHasData, toTrendChartData } from "@/utils/trends";
import { theme } from "@/theme";

interface TrendChartProps {
  series: TrendSeries;
  /** Period labels flagged as anomalies, to emphasize on the line (Req 5.3). */
  anomalyPeriods?: Set<string>;
}

/**
 * A per-metric trend chart with an optional baseline overlay (reference line)
 * and anomaly markers (Req 5.2, 5.3). Shows an explicit empty state when the
 * series has no usable data (Req 5.5).
 */
export function TrendChart({ series, anomalyPeriods }: TrendChartProps) {
  const meta = METRIC_META[series.metric];
  const accent = theme.colors[meta.colorKey];

  if (!seriesHasData(series)) {
    return (
      <View style={styles.card}>
        <Text style={styles.title}>{meta.label}</Text>
        <Text style={styles.empty}>No data for this range.</Text>
      </View>
    );
  }

  const data = toTrendChartData(series.points, { labelEvery: 4, anomalyPeriods }).map((p) =>
    p.anomaly
      ? {
          ...p,
          dataPointColor: theme.colors.danger,
          dataPointRadius: 5,
          showDataPoint: true,
        }
      : p,
  );

  const baseline = series.baselineMean;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.title}>{meta.label}</Text>
        {baseline !== null ? (
          <Text style={styles.baselineLabel}>
            baseline {Math.round(baseline)}
            {meta.unit ? ` ${meta.unit}` : ""}
          </Text>
        ) : null}
      </View>
      <LineChart
        data={data}
        color={accent}
        thickness={2}
        height={140}
        hideDataPoints
        yAxisThickness={0}
        xAxisThickness={0}
        xAxisLabelTextStyle={styles.axisLabel}
        yAxisTextStyle={styles.axisLabel}
        rulesColor={theme.colors.border}
        rulesType="dashed"
        adjustToWidth
        disableScroll
        initialSpacing={8}
        // Baseline overlay as a horizontal reference line.
        showReferenceLine1={baseline !== null}
        referenceLine1Position={baseline ?? 0}
        referenceLine1Config={{
          color: theme.colors.textSecondary,
          dashWidth: 4,
          dashGap: 4,
          thickness: 1,
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(4),
    gap: theme.spacing(2),
  },
  header: { flexDirection: "row", alignItems: "baseline", justifyContent: "space-between" },
  title: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700" },
  baselineLabel: { color: theme.colors.textSecondary, fontSize: theme.font.caption },
  axisLabel: { color: theme.colors.textSecondary, fontSize: 10 },
  empty: { color: theme.colors.textSecondary, fontSize: theme.font.body },
});
