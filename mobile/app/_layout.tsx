import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";

import { useSettings } from "@/api/hooks";
import { theme } from "@/theme";

const queryClient = new QueryClient();

/**
 * First-launch disclaimer gate (Req 12.5): once settings load, if the
 * disclaimer has not been acknowledged, push the disclaimer modal. Runs inside
 * the QueryClientProvider so the hook has a client.
 */
function DisclaimerGate() {
  const settings = useSettings();
  useEffect(() => {
    if (settings.data && !settings.data.disclaimerAckAt) {
      router.push("/disclaimer");
    }
  }, [settings.data]);
  return null;
}

/**
 * Root layout. Wraps the app in React Query and a dark stack navigator.
 */
export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="light" />
      <DisclaimerGate />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: theme.colors.bg },
          headerTintColor: theme.colors.textPrimary,
          contentStyle: { backgroundColor: theme.colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="disclaimer" options={{ presentation: "modal", title: "Disclaimer" }} />
        <Stack.Screen name="emergency" options={{ presentation: "modal", title: "Emergency" }} />
      </Stack>
    </QueryClientProvider>
  );
}
