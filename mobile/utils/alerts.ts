/**
 * Shared alert-state presentation helpers (label + theme color per state).
 * Pure, no React — testable (Task 27) and reused by the dashboard status card
 * and the insights banner.
 */
import type { AlertState } from "@/api/types";
import { theme } from "@/theme";

export interface AlertStateMeta {
  label: string;
  color: string;
  defaultTitle: string;
}

export const ALERT_STATE_META: Record<AlertState, AlertStateMeta> = {
  normal: {
    label: "Normal monitoring",
    color: theme.colors.accentGreen,
    defaultTitle: "Everything looks steady",
  },
  trend_review: {
    label: "Trend review recommended",
    color: theme.colors.warn,
    defaultTitle: "A trend may be worth reviewing",
  },
  attention: {
    label: "Needs further assessment",
    color: theme.colors.danger,
    defaultTitle: "A measurement may need attention",
  },
};

export function alertStateMeta(state: AlertState): AlertStateMeta {
  return ALERT_STATE_META[state];
}
