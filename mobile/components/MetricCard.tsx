import { StyleSheet, Text, View } from "react-native";

import type { MetricType, Reading } from "@/api/types";
import {
  METRIC_META,
  formatMetricValue,
  hasUsableValue,
  qualityLabel,
} from "@/utils/metrics";
import { theme } from "@/theme";

import { MiniTrend } from "./MiniTrend";

interface MetricCardProps {
  metric: MetricType;
  /** Latest reading for this metric, or undefined when none exists. */
  reading?: Reading;
  /** Optional recent values (oldest→newest) for a mini trend chart. */
  series?: (number | null)[];
}

/**
 * A single dashboard metric card: label, current value + unit, a data-quality
 * note when the latest sample is missing/low, and an optional mini trend.
 *
 * Shows an explicit "No data" state rather than a misleading value (Req 1.6).
 */
export function MetricCard({ metric, reading, series }: MetricCardProps) {
  const meta = METRIC_META[metric];
  const accent = theme.colors[meta.colorKey];
  const usable = hasUsableValue(reading);

  const valueText = formatMetricValue(reading?.value ?? null, metric);
  const quality = reading ? qualityLabel(reading.quality) : "No data";

  return (
    <View
      style={styles.card}
      accessibilityRole="summary"
      accessibilityLabel={`${meta.label}: ${usable ? `${valueText} ${meta.unit}` : quality || "No data"}`}
    >
      <Text style={styles.label}>{meta.label}</Text>

      <View style={styles.valueRow}>
        <Text style={[styles.value, { color: usable ? accent : theme.colors.textSecondary }]}>
          {valueText}
        </Text>
        {usable && meta.unit ? <Text style={styles.unit}>{meta.unit}</Text> : null}
      </View>

      {!usable && quality ? <Text style={styles.quality}>{quality}</Text> : null}

      {series && series.length > 1 ? (
        <View style={styles.trend}>
          <MiniTrend values={series} color={accent} />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: 150,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(4),
    gap: theme.spacing(1),
  },
  label: { color: theme.colors.textSecondary, fontSize: theme.font.caption, fontWeight: "600" },
  valueRow: { flexDirection: "row", alignItems: "flex-end", gap: theme.spacing(1) },
  value: { fontSize: theme.font.h1, fontWeight: "700" },
  unit: { color: theme.colors.textSecondary, fontSize: theme.font.body, marginBottom: theme.spacing(1) },
  quality: { color: theme.colors.warn, fontSize: theme.font.caption },
  trend: { marginTop: theme.spacing(2) },
});
