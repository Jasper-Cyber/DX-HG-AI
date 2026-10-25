import { StyleSheet, Text, View } from "react-native";

import type { DispatchEvent } from "@/api/types";
import { SimulatedDispatchBadge } from "@/components/SimulatedDispatchBadge";
import { theme } from "@/theme";

/**
 * Past-dispatch history (Task 25, Owner: maiabrunne).
 * Lists each dispatch with timestamp, recipient, routing reason, channel and status
 * so the flow is auditable (Req 11.7). Matches the backend's flat HistoryItem shape.
 */
const REASON_LABEL: Record<string, string> = {
  preferred_doctor_reachable: "Preferred doctor (reachable)",
  nearest_capable_hospital: "Nearest capable hospital",
};

export function DispatchHistoryList({ events }: { events: DispatchEvent[] }) {
  if (events.length === 0) {
    return <Text style={styles.empty}>No dispatches yet.</Text>;
  }
  return (
    <View style={styles.list}>
      {events.map((e) => (
        <View key={e.id ?? Math.random()} style={styles.item}>
          <View style={styles.row}>
            <Text style={styles.recipient} numberOfLines={1}>
              {e.recipientProviderId != null
                ? `Provider #${e.recipientProviderId}`
                : `Dispatch #${e.id ?? "?"}`}
            </Text>
            <SimulatedDispatchBadge channel={e.channel} />
          </View>
          <Text style={styles.meta}>{formatTime(e.createdAt)}</Text>
          <Text style={styles.meta}>
            Routing: {REASON_LABEL[e.routingReason] ?? e.routingReason}
          </Text>
          <Text style={[styles.status, statusStyle(e.status)]}>Status: {e.status}</Text>
        </View>
      ))}
    </View>
  );
}

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function statusStyle(status: string) {
  if (status === "sent") return { color: theme.colors.accentGreen };
  if (status === "cancelled" || status === "failed") return { color: theme.colors.danger };
  return { color: theme.colors.warn };
}

const styles = StyleSheet.create({
  list: { gap: theme.spacing(2) },
  item: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(3),
    gap: 2,
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  recipient: { color: theme.colors.textPrimary, fontFamily: theme.type.body, fontSize: theme.font.body, fontWeight: "700", flexShrink: 1 },
  meta: { color: theme.colors.textSecondary, fontFamily: theme.type.mono, fontSize: theme.font.caption },
  status: { fontFamily: theme.type.mono, fontSize: theme.font.caption, fontWeight: "600", marginTop: 2 },
  empty: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: theme.font.body },
});
