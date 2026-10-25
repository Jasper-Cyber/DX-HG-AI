import { ActivityIndicator, View } from "react-native";
import { useFonts } from "expo-font";
import { SpaceGrotesk_500Medium } from "@expo-google-fonts/space-grotesk/500Medium";
import { PlusJakartaSans_400Regular } from "@expo-google-fonts/plus-jakarta-sans/400Regular";
import { JetBrainsMono_400Regular } from "@expo-google-fonts/jetbrains-mono/400Regular";
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
 * Root layout. Wraps the app in React Query and a light stack navigator.
 */
export default function RootLayout() {
  const [loaded, fontError] = useFonts({
    SpaceGrotesk: SpaceGrotesk_500Medium,
    PlusJakartaSans: PlusJakartaSans_400Regular,
    JetBrainsMono: JetBrainsMono_400Regular,
  });
  if (!loaded && !fontError) return <View style={{ flex: 1, backgroundColor: theme.colors.bg, alignItems: "center", justifyContent: "center" }}><ActivityIndicator color={theme.colors.accent} /></View>;
  return (
    <QueryClientProvider client={queryClient}>
      <View style={{ flex: 1, backgroundColor: theme.colors.bg, alignItems: "center" }}>
      <View style={{ flex: 1, width: "100%", maxWidth: 520, backgroundColor: theme.colors.bg }}>
      <StatusBar style="dark" />
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
      </View>
      </View>
    </QueryClientProvider>
  );
}
