/**
 * Dark-blue healthcare theme tokens for HeartGuardian AI.
 * Colors chosen for AA-contrast text on dark backgrounds.
 */
export const theme = {
  colors: {
    bg: "#0A1628", // deep navy background
    surface: "#122236", // card surface
    surfaceAlt: "#1A2E47",
    border: "#243B59",
    textPrimary: "#F2F6FC", // high-contrast on bg (AA)
    textSecondary: "#9FB3CC",
    accent: "#38BDF8", // cyan accent (heart rate)
    accentGreen: "#34D399", // HRV
    warn: "#FBBF24", // trend-review
    danger: "#F87171", // attention
    experimental: "#C084FC", // "simulated / experimental" labels
  },
  spacing: (n: number) => n * 4,
  radius: { sm: 8, md: 12, lg: 16 },
  font: {
    h1: 28,
    h2: 20,
    body: 15,
    caption: 12,
  },
} as const;

export type Theme = typeof theme;
