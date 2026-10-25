import type { MetricType } from "./api/types";

/** Warm, light surfaces with high-contrast teal data accents. */
export const theme = {
  colors: {
    onAccent: "#FFFFFF",
    accentSoft: "#E3F1EA",
    dangerSoft: "#FFF0ED",
    bg: "#ECEAE3",
    surface: "#FFFFFF",
    surfaceAlt: "#ECF2EE",
    inset: "#F4F7F5",
    border: "#B9C5BD",
    controlBorder: "#748078",
    textPrimary: "#182922",
    textSecondary: "#46574E",
    muted: "#52645A",
    accent: "#16715F",
    accentGreen: "#246E84",
    pale: "#155D50",
    warn: "#8A5909",
    danger: "#B54441",
    experimental: "#52645D",
  },
  type: { heading: "SpaceGrotesk", body: "PlusJakartaSans", mono: "JetBrainsMono" },
  spacing: (n: number) => n * 4,
  radius: { sm: 8, md: 16, lg: 22 },
  font: { h1: 26, h2: 18, body: 14, caption: 12 },
} as const;
export type Theme = typeof theme;

/** Metric identity is independent of clinical status. Keep labels alongside color.
 * Ink colors support small text on white and their paired pale surface.
 */
export const metricPalette = {
  hr:       { ink: "#A83258", soft: "#FCEEF2", border: "#EBC5D1" },
  hrv:      { ink: "#7450A3", soft: "#F3EEF9", border: "#DACCEB" },
  spo2:     { ink: "#176D95", soft: "#EAF4FA", border: "#BDDDEB" },
  rhythm:   { ink: "#16715F", soft: "#E9F5EF", border: "#C0DFD3" },
  vo2max:   { ink: "#945310", soft: "#FFF3E4", border: "#EBD2AC" },
  sleep:    { ink: "#4D5CAA", soft: "#EEF0FC", border: "#CDD3EE" },
  activity: { ink: "#526D30", soft: "#F0F5E9", border: "#D4E1C0" },
} satisfies Record<MetricType, { ink: string; soft: string; border: string }>;

/** Contrasting companions for a second series inside each metric's chart. */
export const chartCompanion: Record<MetricType, string> = {
  hr: "#176D95", hrv: "#945310", spo2: "#A83258", rhythm: "#7450A3",
  vo2max: "#176D95", sleep: "#945310", activity: "#7450A3",
};
export const chartSeries = {
  minimum: "#7450A3", average: "#176D95", maximum: "#A83258",
  daily: "#945310", previous: "#7450A3", current: "#16715F",
} as const;
