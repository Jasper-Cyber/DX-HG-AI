import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Scenario } from "@/api/types";
import { theme } from "@/theme";
import { Icon } from "./Icon";
export const SCENARIOS = [
  { key: "A" as Scenario, title: "Normal Baseline", tag: "BASELINE", blurb: "Synthetic metrics fluctuate around a steady personal baseline.", details: ["STEADY HR", "BALANCED HRV", "REGULAR RHYTHM"], color: theme.colors.accent },
  { key: "B" as Scenario, title: "Gradual Deviation", tag: "DRIFT", blurb: "Resting heart rate drifts up while HRV and sleep decline over simulated weeks.", details: ["HR ↑", "HRV ↓", "SLEEP ↓"], color: theme.colors.warn },
  { key: "C" as Scenario, title: "Rhythm Irregularity", tag: "EVENT", blurb: "Intermittent irregular-rhythm flags create a synthetic pattern for the analysis engine to review.", details: ["RHYTHM FLAGS", "PERIODIC BURSTS", "SIMULATED"], color: theme.colors.danger },
];
export function ScenarioPicker({ value, onChange, disabled }: { value: Scenario; onChange: (s: Scenario) => void; disabled?: boolean }) {
  return <View style={s.list} accessibilityRole="radiogroup">{SCENARIOS.map(item => {
    const selected = item.key === value;
    return <Pressable key={item.key} onPress={() => onChange(item.key)} disabled={disabled} accessibilityRole="radio" accessibilityState={{ selected, disabled: !!disabled }} accessibilityLabel={`Scenario ${item.key}: ${item.title}`} style={[s.card, selected && { borderColor: item.color, backgroundColor: theme.colors.accentSoft }, disabled && { opacity: .5 }]}>
      <View style={s.row}><View style={[s.radio, selected && { borderColor: item.color, borderWidth: 4 }]} /><Text style={s.title}>Scenario {item.key}</Text><Text style={[s.tag, { color: item.color }]}>{item.tag}</Text><View style={{ flex: 1 }} />{selected && <Icon name="check" color={item.color} size={16} />}</View>
      <Text style={s.name}>{item.title}</Text><Text style={s.blurb}>{item.blurb}</Text>
      <View style={s.details}>{item.details.map(text => <Text key={text} style={[s.detail, { color: item.color }]}>{text}</Text>)}</View>
    </Pressable>;
  })}</View>;
}
const s = StyleSheet.create({
  list: { gap: 14 }, card: { backgroundColor: theme.colors.surface, borderRadius: 17, borderWidth: 1, borderColor: theme.colors.border, padding: 18, gap: 10 },
  row: { flexDirection: "row", alignItems: "center", gap: 8 }, radio: { width: 13, height: 13, borderRadius: 8, backgroundColor: theme.colors.surfaceAlt, borderWidth: 1, borderColor: theme.colors.border },
  title: { fontFamily: theme.type.heading, color: theme.colors.textPrimary, fontSize: 18 },
  tag: { fontFamily: theme.type.mono, fontSize: 11, letterSpacing: .5, backgroundColor: theme.colors.inset, paddingHorizontal: 6, paddingVertical: 4, borderRadius: 6 },
  name: { fontFamily: theme.type.body, color: theme.colors.textPrimary, fontSize: 12, marginLeft: 21 },
  blurb: { fontFamily: theme.type.body, color: theme.colors.textSecondary, fontSize: 12, lineHeight: 20 },
  details: { flexDirection: "row", justifyContent: "space-between", backgroundColor: theme.colors.inset, padding: 12, borderRadius: 9, gap: 5 },
  detail: { fontFamily: theme.type.mono, fontSize: 11, flexShrink: 1 },
});
