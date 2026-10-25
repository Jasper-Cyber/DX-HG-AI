import { StyleSheet, Text, TextInput, View, type KeyboardTypeOptions } from "react-native";

import { theme } from "@/theme";

interface LabeledInputProps {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  error?: string;
  keyboardType?: KeyboardTypeOptions;
}

/** A labeled text field with an inline validation error (used by the care forms). */
export function LabeledInput({
  label,
  value,
  onChangeText,
  placeholder,
  error,
  keyboardType,
}: LabeledInputProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, error ? styles.inputError : null]}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textSecondary}
        keyboardType={keyboardType}
        accessibilityLabel={label}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: theme.spacing(1) },
  label: { color: theme.colors.textSecondary, fontSize: theme.font.caption, fontWeight: "600" },
  input: {
    backgroundColor: theme.colors.bg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.sm,
    paddingVertical: theme.spacing(2),
    paddingHorizontal: theme.spacing(3),
    color: theme.colors.textPrimary,
    fontSize: theme.font.body,
  },
  inputError: { borderColor: theme.colors.danger },
  error: { color: theme.colors.danger, fontSize: theme.font.caption },
});
