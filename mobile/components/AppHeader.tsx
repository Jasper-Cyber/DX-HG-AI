import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Icon } from "./Icon";
import { theme } from "@/theme";

export function AppHeader({ title }: { title: string }) {
  return <View style={s.header}>
    <View style={s.logo}><Icon name="heart" size={24} /><View style={s.pulse}><Icon name="pulse" size={16} /></View></View>
    <View style={s.brand}><View style={s.row}><Text style={s.name}>HeartGuardian</Text><Text style={s.ai}>AI</Text></View><Text style={s.subtitle}>{title}</Text></View>
    <View style={s.source}><View style={s.dot} /><Text style={s.sourceText}>DEMO</Text></View>
    <Pressable accessibilityRole="button" accessibilityLabel="Open settings" onPress={() => router.push("/(tabs)/profile")} style={({ pressed }) => [s.avatar, pressed && { backgroundColor: theme.colors.pale }]}><Icon name="user" color={theme.colors.onAccent} size={17} /></Pressable>
  </View>;
}
const s = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 16, paddingVertical: 14, backgroundColor: theme.colors.bg },
  logo: { width: 36, height: 36, borderRadius: 10, backgroundColor: theme.colors.accentSoft, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: theme.colors.border },
  pulse: { position: "absolute", backgroundColor: theme.colors.accentSoft },
  brand: { flex: 1 }, row: { flexDirection: "row", alignItems: "center", gap: 5 },
  name: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: 17 },
  ai: { color: theme.colors.pale, fontFamily: theme.type.mono, fontSize: 11, backgroundColor: theme.colors.surfaceAlt, borderRadius: 5, paddingHorizontal: 5, paddingVertical: 2 },
  subtitle: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: 12, marginTop: 3 },
  source: { backgroundColor: theme.colors.accentSoft, paddingHorizontal: 9, paddingVertical: 5, borderRadius: 20, flexDirection: "row", alignItems: "center", gap: 5 },
  dot: { width: 5, height: 5, borderRadius: 3, backgroundColor: theme.colors.accentGreen },
  sourceText: { color: theme.colors.accentGreen, fontFamily: theme.type.mono, fontSize: 11, letterSpacing: 1 },
  avatar: { width: 44, height: 44, borderRadius: 16, backgroundColor: theme.colors.accent, alignItems: "center", justifyContent: "center" },
});
