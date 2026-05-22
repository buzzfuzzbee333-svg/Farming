import { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
} from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, IdleGame } from "@/src/lib/api";
import { colors, mono, formatMinutes, formatUSD } from "@/src/lib/theme";
import { Card, SectionLabel, PrimaryButton } from "@/src/components/ui";

export default function GamesScreen() {
  const router = useRouter();
  const [games, setGames] = useState<IdleGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const g = await api.listGames();
      setGames(g);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            load();
          }}
          tintColor={colors.accent}
        />
      }
      testID="games-screen"
    >
      <View style={styles.headerRow}>
        <SectionLabel>// IDLE_GAMES [{games.length}]</SectionLabel>
        <TouchableOpacity
          onPress={() => router.push("/game/new")}
          style={styles.addBtn}
          testID="add-game-btn"
          activeOpacity={0.7}
        >
          <Ionicons name="add" size={16} color={colors.accent} />
          <Text style={styles.addBtnText}>NEW</Text>
        </TouchableOpacity>
      </View>

      {games.length === 0 ? (
        <Card>
          <Text style={styles.emptyText}>
            No games configured. Add your first idle game to begin.
          </Text>
          <PrimaryButton
            label="+ Add First Game"
            onPress={() => router.push("/game/new")}
            testID="add-first-game-btn"
            style={{ marginTop: 12 }}
          />
        </Card>
      ) : (
        games.map((g) => (
          <TouchableOpacity
            key={g.id}
            activeOpacity={0.7}
            onPress={() => router.push(`/game/${g.id}`)}
            testID={`game-card-${g.id}`}
          >
            <Card style={styles.gameCard}>
              <View style={styles.gameTopRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.gameName}>{g.name}</Text>
                  <Text style={styles.gamePkg} numberOfLines={1}>
                    {g.package_name}
                  </Text>
                </View>
                <View
                  style={[
                    styles.activeDot,
                    {
                      backgroundColor: g.is_active
                        ? colors.accent
                        : colors.textTertiary,
                    },
                  ]}
                />
              </View>
              <View style={styles.gameMetaRow}>
                <View style={styles.gameMeta}>
                  <Text style={styles.gameMetaLabel}>EST</Text>
                  <Text style={styles.gameMetaValue}>
                    {formatMinutes(g.est_minutes)}
                  </Text>
                </View>
                <View style={styles.divider} />
                <View style={styles.gameMeta}>
                  <Text style={styles.gameMetaLabel}>PAYOUT</Text>
                  <Text
                    style={[styles.gameMetaValue, { color: colors.accent }]}
                  >
                    {formatUSD(g.base_payout_cents)}
                  </Text>
                </View>
                <View style={styles.divider} />
                <View style={styles.gameMeta}>
                  <Text style={styles.gameMetaLabel}>STATUS</Text>
                  <Text
                    style={[
                      styles.gameMetaValue,
                      { color: g.is_active ? colors.accent : colors.textTertiary },
                    ]}
                  >
                    {g.is_active ? "ARMED" : "IDLE"}
                  </Text>
                </View>
              </View>
            </Card>
          </TouchableOpacity>
        ))
      )}
      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 64 },
  loading: {
    flex: 1,
    backgroundColor: colors.bg,
    justifyContent: "center",
    alignItems: "center",
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  addBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: colors.accentBorder,
    backgroundColor: colors.accentSoft,
    borderRadius: 3,
  },
  addBtnText: {
    fontFamily: mono,
    color: colors.accent,
    fontSize: 11,
    letterSpacing: 1.5,
    fontWeight: "700",
  },
  emptyText: {
    color: colors.textSecondary,
    fontFamily: mono,
    fontSize: 12,
    textAlign: "center",
  },
  gameCard: { marginBottom: 10 },
  gameTopRow: { flexDirection: "row", alignItems: "center" },
  gameName: {
    fontFamily: mono,
    color: colors.text,
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: -0.3,
  },
  gamePkg: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 11,
    marginTop: 2,
  },
  activeDot: { width: 8, height: 8, borderRadius: 4 },
  gameMetaRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  gameMeta: { flex: 1 },
  gameMetaLabel: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 9,
    letterSpacing: 1.5,
    marginBottom: 2,
  },
  gameMetaValue: {
    fontFamily: mono,
    color: colors.text,
    fontSize: 13,
    fontWeight: "700",
  },
  divider: {
    width: 1,
    height: 24,
    backgroundColor: colors.border,
    marginHorizontal: 8,
  },
});
