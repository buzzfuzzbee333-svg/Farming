import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors, mono } from "@/src/lib/theme";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg, borderBottomColor: colors.border, borderBottomWidth: 1 },
        headerTitleStyle: {
          color: colors.text,
          fontFamily: mono,
          fontSize: 14,
          letterSpacing: 2,
        },
        tabBarStyle: {
          backgroundColor: colors.bg,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 64,
        },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textTertiary,
        tabBarLabelStyle: {
          fontFamily: mono,
          fontSize: 10,
          letterSpacing: 1.5,
          textTransform: "uppercase",
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "DASHBOARD",
          tabBarLabel: "Dash",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="pulse" size={size} color={color} />
          ),
          tabBarButtonTestID: "nav-dashboard",
        }}
      />
      <Tabs.Screen
        name="games"
        options={{
          title: "GAMES",
          tabBarLabel: "Games",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="game-controller-outline" size={size} color={color} />
          ),
          tabBarButtonTestID: "nav-games",
        }}
      />
      <Tabs.Screen
        name="sessions"
        options={{
          title: "SESSIONS",
          tabBarLabel: "Sessions",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="time-outline" size={size} color={color} />
          ),
          tabBarButtonTestID: "nav-sessions",
        }}
      />
    </Tabs>
  );
}
