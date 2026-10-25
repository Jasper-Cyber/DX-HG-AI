import { StyleSheet, Text, View } from "react-native";
import { theme } from "@/theme";
import { Icon } from "./Icon";
export function SimulatedDataRibbon() {
  return <View style={s.ribbon}><Icon name="shield" size={11} color={theme.colors.pale} /><Text style={s.text}>SIMULATED DATA — experimental prototype, not medical advice</Text></View>;
}
const s = StyleSheet.create({
  ribbon: { backgroundColor: theme.colors.accentSoft, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 5, paddingVertical: 7, paddingHorizontal: 8 },
  text: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 11, flexShrink: 1 },
});
