import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { colors } from "@/src/lib/theme";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerTintColor: colors.text,
          headerTitleStyle: { color: colors.text },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="game/[id]"
          options={{ title: "GAME DETAIL", headerBackTitle: "Back" }}
        />
        <Stack.Screen
          name="game/new"
          options={{ title: "NEW GAME", presentation: "modal" }}
        />
        <Stack.Screen
          name="session/new"
          options={{ title: "START SESSION", presentation: "modal" }}
        />
      </Stack>
    </SafeAreaProvider>
  );
}
