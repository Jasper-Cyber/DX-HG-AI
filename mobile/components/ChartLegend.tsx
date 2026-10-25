import { StyleSheet, Text, View } from "react-native";
import { theme } from "@/theme";

type LegendItem = { label: string; color: string; mark?: "line" | "dash" | "dot" | "bar" };
/** Match both color and geometry to the plotted series. */
export function ChartLegend({ items }: { items: LegendItem[] }) {
  return <View style={s.row}>{items.map(({ label, color, mark = "line" }) =>
    <View key={label} style={s.item}>
      {mark === "dash" ? <View style={s.dashes}>{[0, 1, 2].map(i => <View key={i} style={{ width: 5, height: 3, backgroundColor: color }} />)}</View>
        : <View style={{ width: mark === "dot" ? 8 : 20, height: mark === "dot" ? 8 : mark === "bar" ? 10 : 3, borderRadius: mark === "dot" ? 4 : 2, backgroundColor: color }} />}
      <Text style={s.label}>{label}</Text>
    </View>
  )}</View>;
}
const s = StyleSheet.create({
  row: { flexDirection: "row", flexWrap: "wrap", gap: 12, paddingVertical: 5 },
  item: { flexDirection: "row", alignItems: "center", gap: 6 },
  dashes: { flexDirection: "row", gap: 2 },
  label: { fontFamily: theme.type.body, fontSize: 12, color: theme.colors.textSecondary },
});
