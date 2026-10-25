import { Tabs } from "expo-router";

import { theme } from "@/theme";

/**
 * Bottom tab navigation.
 *
 * Shared file (see TEAM.md): when you add a screen, append ONE <Tabs.Screen>
 * entry here to keep merges conflict-free.
 */
export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: theme.colors.bg },
        headerTintColor: theme.colors.textPrimary,
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.border,
        },
        tabBarActiveTintColor: theme.colors.accent,
        tabBarInactiveTintColor: theme.colors.textSecondary,
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Dashboard" }} />
      <Tabs.Screen name="insights" options={{ title: "Insights" }} />
      <Tabs.Screen name="history" options={{ title: "History" }} />
      <Tabs.Screen name="simulator" options={{ title: "Simulator" }} />
      <Tabs.Screen name="profile" options={{ title: "Settings" }} />
    </Tabs>
  );
}
