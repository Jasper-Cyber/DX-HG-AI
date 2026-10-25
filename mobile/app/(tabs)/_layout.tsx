import { Tabs } from "expo-router";
import { Icon, type IconName } from "@/components/Icon";
import { theme } from "@/theme";
const tabs: { name: string; title: string; icon: IconName }[] = [
  { name: "index", title: "Dashboard", icon: "heart" },
  { name: "insights", title: "Insights", icon: "sparkles" },
  { name: "history", title: "History", icon: "chart" },
  { name: "simulator", title: "Simulator", icon: "sliders" },
  { name: "profile", title: "Settings", icon: "settings" },
];
export default function TabsLayout() {
  return <Tabs screenOptions={{
    headerShown: false,
    tabBarStyle: { backgroundColor: theme.colors.surface, borderTopColor: theme.colors.border, height: 76, paddingBottom: 12, paddingTop: 9 },
    tabBarActiveBackgroundColor: theme.colors.accentSoft,
    tabBarItemStyle: { borderRadius: 12, marginHorizontal: 2 },
    tabBarLabelStyle: { fontFamily: theme.type.mono, fontSize: 11, letterSpacing: 0 },
    tabBarActiveTintColor: theme.colors.accent,
    tabBarInactiveTintColor: theme.colors.textSecondary,
  }}>{tabs.map(t => <Tabs.Screen key={t.name} name={t.name} options={{ title: t.title, tabBarIcon: ({ color }) => <Icon name={t.icon} color={color} size={21} /> }} />)}</Tabs>;
}
