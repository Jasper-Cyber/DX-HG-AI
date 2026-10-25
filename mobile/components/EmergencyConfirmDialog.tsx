import { useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { theme } from "@/theme";

/**
 * Confirm-with-countdown dialog gating any dispatch (Task 25, Owner: maiabrunne).
 *
 * No dispatch happens without explicit confirmation (Req 11.5). The dialog shows a
 * short countdown and a Cancel control that stops the dispatch. The countdown here
 * is informational (it does NOT auto-dispatch): the user must still press Confirm,
 * keeping a human firmly in the loop. Cancel is always available.
 */
export function EmergencyConfirmDialog({
  visible,
  recipientName,
  channel,
  countdownSeconds = 5,
  onConfirm,
  onCancel,
  busy = false,
}: {
  visible: boolean;
  recipientName: string;
  channel: "simulated" | "real";
  countdownSeconds?: number;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  const [remaining, setRemaining] = useState(countdownSeconds);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!visible) return;
    setRemaining(countdownSeconds);
    timer.current = setInterval(() => {
      setRemaining((r) => (r > 0 ? r - 1 : 0));
    }, 1000);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [visible, countdownSeconds]);

  if (!visible) return null;

  const confirmReady = remaining === 0;

  return (
    <View style={styles.backdrop} accessibilityViewIsModal>
      <View style={styles.dialog} accessibilityRole="alert">
        <Text style={styles.title}>Confirm {channel === "real" ? "dispatch" : "simulated dispatch"}</Text>
        <Text style={styles.body}>
          This will {channel === "real" ? "contact" : "record a simulated notification to"}{" "}
          <Text style={styles.recipient}>{recipientName}</Text> and share your care-profile
          information and location. You can cancel at any time.
        </Text>

        {channel === "simulated" ? (
          <Text style={styles.simNote}>
            Simulated: nothing is sent to a real recipient; the dispatch is recorded in-app.
          </Text>
        ) : null}

        <View style={styles.actions}>
          <Pressable
            onPress={onCancel}
            style={[styles.btn, styles.cancel]}
            accessibilityRole="button"
            accessibilityLabel="Cancel dispatch"
          >
            <Text style={styles.cancelText}>Cancel</Text>
          </Pressable>
          <Pressable
            onPress={onConfirm}
            disabled={!confirmReady || busy}
            style={[styles.btn, styles.confirm, (!confirmReady || busy) && styles.confirmDisabled]}
            accessibilityRole="button"
            accessibilityState={{ disabled: !confirmReady || busy }}
            accessibilityLabel="Confirm dispatch"
          >
            <Text style={styles.confirmText}>
              {busy ? "Sending…" : confirmReady ? "Confirm" : `Confirm (${remaining})`}
            </Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(5, 11, 20, 0.8)",
    justifyContent: "center",
    padding: theme.spacing(5),
  },
  dialog: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.danger,
    padding: theme.spacing(4),
    gap: theme.spacing(3),
  },
  title: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700" },
  body: { color: theme.colors.textSecondary, fontSize: theme.font.body, lineHeight: 20 },
  recipient: { color: theme.colors.textPrimary, fontWeight: "700" },
  simNote: { color: theme.colors.experimental, fontSize: theme.font.caption, fontWeight: "600" },
  actions: { flexDirection: "row", gap: theme.spacing(3), marginTop: theme.spacing(1) },
  btn: { flex: 1, paddingVertical: theme.spacing(3), borderRadius: theme.radius.md, alignItems: "center" },
  cancel: { backgroundColor: theme.colors.surfaceAlt, borderWidth: 1, borderColor: theme.colors.border },
  cancelText: { color: theme.colors.textPrimary, fontSize: theme.font.body, fontWeight: "700" },
  confirm: { backgroundColor: theme.colors.danger },
  confirmDisabled: { opacity: 0.5 },
  confirmText: { color: theme.colors.bg, fontSize: theme.font.body, fontWeight: "700" },
});
