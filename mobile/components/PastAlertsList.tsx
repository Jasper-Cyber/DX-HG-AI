import { StyleSheet, Text, View } from "react-native";

import type { AlertSummary } from "@/api/types";
import { alertStateMeta } from "@/utils/alerts";
import { theme } from "@/theme";

interface PastAlertsListProps {
  alerts: AlertSummary[];
}

/** Compact list of past alerts for the History screen (Req 5.3). */
export function PastAlertsList({ alerts }: PastAlertsListProps) {
  if (alerts.length === 0) {
    return <Text style={styles.empty}>No past alerts.</Text>;
  }

  return (
    <View style={styles.list}>
      {alerts.map((a, i) => {
        const meta = alertStateMeta(a.state);
        return (
          <View key={a.id ?? i} style={styles.row}>
            <View style={[styles.dot, { backgroundColor: meta.color }]} />
            <View style={styles.rowText}>
              <Text style={styles.title}>{a.title || meta.defaultTitle}</Text>
              {a.createdAt ? <Text style={styles.time}>{formatTime(a.createdAt)}</Text> : null}
            </View>
          </View>
        );
      })}
    </View>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString();
}

const styles = StyleSheet.create({
  list: { gap: theme.spacing(2) },
  row: { padding: 12, borderRadius: 10, backgroundColor: theme.colors.surfaceAlt, flexDirection: "row", alignItems: "center", gap: theme.spacing(3) },
  dot: { width: 10, height: 10, borderRadius: 5 },
  rowText: { flex: 1 },
  title: { color: theme.colors.textPrimary, fontFamily: theme.type.body, fontSize: 11 },
  time: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: 11, marginTop: 5 },
  empty: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 11 },
});
