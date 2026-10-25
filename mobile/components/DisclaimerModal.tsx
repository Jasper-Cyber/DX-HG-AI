import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import {
  DISCLAIMER_ACK_LABEL,
  DISCLAIMER_PARAGRAPHS,
  DISCLAIMER_TITLE,
} from "@/utils/disclaimer";
import { theme } from "@/theme";

interface DisclaimerModalProps {
  /** Whether to show the acknowledgement button (first-launch gate) or just the text. */
  showAck?: boolean;
  /** Called when the user acknowledges. */
  onAcknowledge?: () => void;
  /** Disable the ack button while the acknowledgement request is in flight. */
  acknowledging?: boolean;
}

/**
 * Plain-language experimental disclaimer (Req 12). Rendered both as the
 * first-launch gate (with an acknowledge button) and as a read-only view
 * reachable from Settings (showAck=false).
 */
export function DisclaimerModal({ showAck = true, onAcknowledge, acknowledging }: DisclaimerModalProps) {
  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>{DISCLAIMER_TITLE}</Text>
        {DISCLAIMER_PARAGRAPHS.map((p, i) => (
          <Text key={i} style={styles.paragraph}>
            {p}
          </Text>
        ))}
      </ScrollView>

      {showAck ? (
        <Pressable
          style={[styles.ack, acknowledging && styles.ackDisabled]}
          onPress={onAcknowledge}
          disabled={acknowledging}
          accessibilityRole="button"
          accessibilityLabel={DISCLAIMER_ACK_LABEL}
        >
          <Text style={styles.ackText}>{DISCLAIMER_ACK_LABEL}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(5), gap: theme.spacing(4) },
  title: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  paragraph: { color: theme.colors.textPrimary, fontSize: theme.font.body, lineHeight: 24 },
  ack: {
    margin: theme.spacing(4),
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.md,
    paddingVertical: theme.spacing(4),
    alignItems: "center",
  },
  ackDisabled: { opacity: 0.5 },
  ackText: { color: theme.colors.bg, fontSize: theme.font.body, fontWeight: "800" },
});
