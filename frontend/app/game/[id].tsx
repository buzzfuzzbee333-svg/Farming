import { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
} from "react-native";
import {
  useLocalSearchParams,
  useRouter,
  useFocusEffect,
  Stack,
} from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, IdleGame, IdleMilestone } from "@/src/lib/api";
import {
  colors,
  mono,
  formatMinutes,
  formatUSD,
} from "@/src/lib/theme";
import {
  Card,
  SectionLabel,
  PrimaryButton,
  SecondaryButton,
} from "@/src/components/ui";

export default function GameDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [game, setGame] = useState<IdleGame | null>(null);
  const [milestones, setMilestones] = useState<IdleMilestone[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [g, m] = await Promise.all([api.getGame(id), api.listMilestones(id)]);
      setGame(g);
      setMilestones(m);
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const toggleActive = async () => {
    if (!game) return;
    const updated = await api.updateGame(game.id, { is_active: !game.is_active });
    setGame(updated);
  };

  const handleDelete = () => {
    if (!game) return;
    Alert.alert(
      "Delete game?",
      `This will remove ${game.name} and all its sessions/milestones.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            await api.deleteGame(game.id);
            router.back();
          },
        },
      ]
    );
  };

  const toggleMilestone = async (m: IdleMilestone) => {
    const updated = await api.updateMilestone(m.id, { completed: !m.completed });
    setMilestones((prev) => prev.map((x) => (x.id === m.id ? updated : x)));
  };

  if (loading || !game) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  const configString = JSON.stringify(game.config_json, null, 2);

  return (
    <>
      <Stack.Screen options={{ title: game.name.toUpperCase() }} />
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        testID="game-detail-screen"
      >
        {/* Header */}
        <Card>
          <View style={styles.headerRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.gameName}>{game.name}</Text>
              <Text style={styles.gamePkg}>{game.package_name}</Text>
            </View>
            <TouchableOpacity
              onPress={toggleActive}
              style={[
                styles.toggleChip,
                {
                  backgroundColor: game.is_active
                    ? colors.accentSoft
                    : colors.zincBadge,
                  borderColor: game.is_active
                    ? colors.accentBorder
                    : colors.zincBadgeBorder,
                },
              ]}
              testID="toggle-active-btn"
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.dot,
                  {
                    backgroundColor: game.is_active
                      ? colors.accent
                      : colors.textTertiary,
                  },
                ]}
              />
              <Text
                style={[
                  styles.toggleText,
                  {
                    color: game.is_active ? colors.accent : colors.textSecondary,
                  },
                ]}
              >
                {game.is_active ? "ACTIVE" : "PAUSED"}
              </Text>
            </TouchableOpacity>
          </View>
          <View style={styles.metaRow}>
            <View style={styles.metaCell}>
              <Text style={styles.metaLabel}>EST</Text>
              <Text style={styles.metaValue}>
                {formatMinutes(game.est_minutes)}
              </Text>
            </View>
            <View style={styles.divider} />
            <View style={styles.metaCell}>
              <Text style={styles.metaLabel}>PAYOUT</Text>
              <Text style={[styles.metaValue, { color: colors.accent }]}>
                {formatUSD(game.base_payout_cents)}
              </Text>
            </View>
            <View style={styles.divider} />
            <View style={styles.metaCell}>
              <Text style={styles.metaLabel}>PLATFORM</Text>
              <Text style={styles.metaValue}>
                {game.platform.toUpperCase()}
              </Text>
            </View>
          </View>
        </Card>

        <PrimaryButton
          label="▶  Start Session"
          onPress={() =>
            router.push({
              pathname: "/session/new",
              params: { game_id: game.id },
            })
          }
          testID="start-game-session-btn"
          style={{ marginTop: 16 }}
        />

        {/* Config */}
        <SectionLabel style={{ marginTop: 24, marginBottom: 8 }}>
          // CONFIG.JSON
        </SectionLabel>
        <View style={styles.codeBlock} testID="config-viewer">
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <Text selectable style={styles.codeText}>
              {configString}
            </Text>
          </ScrollView>
        </View>

        {/* Milestones */}
        <View style={styles.milestoneHeader}>
          <SectionLabel>// MILESTONES [{milestones.length}]</SectionLabel>
        </View>
        {milestones.length === 0 ? (
          <Card>
            <Text style={styles.emptyText}>No milestones configured.</Text>
          </Card>
        ) : (
          milestones.map((m) => (
            <TouchableOpacity
              key={m.id}
              activeOpacity={0.8}
              onPress={() => toggleMilestone(m)}
              testID={`milestone-item-${m.id}`}
            >
              <Card style={styles.milestone}>
                <View
                  style={[
                    styles.checkbox,
                    m.completed && {
                      backgroundColor: colors.accent,
                      borderColor: colors.accent,
                    },
                  ]}
                >
                  {m.completed && (
                    <Ionicons name="checkmark" size={14} color="#000" />
                  )}
                </View>
                <View style={{ flex: 1 }}>
                  <Text
                    style={[
                      styles.mLabel,
                      m.completed && {
                        textDecorationLine: "line-through",
                        color: colors.textTertiary,
                      },
                    ]}
                  >
                    {m.order_index}. {m.label}
                  </Text>
                  <Text style={styles.mDesc} numberOfLines={2}>
                    {m.target_desc}
                  </Text>
                  <View style={styles.mMetaRow}>
                    <Text style={styles.mMeta}>
                      {formatMinutes(m.est_minutes)}
                    </Text>
                    <Text style={styles.mMeta}>·</Text>
                    <Text style={[styles.mMeta, { color: colors.accent }]}>
                      {formatUSD(m.payout_cents)}
                    </Text>
                  </View>
                </View>
              </Card>
            </TouchableOpacity>
          ))
        )}

        <SecondaryButton
          label="🗑  Delete Game"
          onPress={handleDelete}
          testID="delete-game-btn"
          style={{ marginTop: 24, borderColor: colors.redBorder }}
        />
        <View style={{ height: 32 }} />
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16 },
  loading: {
    flex: 1,
    backgroundColor: colors.bg,
    justifyContent: "center",
    alignItems: "center",
  },
  headerRow: { flexDirection: "row", alignItems: "center" },
  gameName: {
    fontFamily: mono,
    color: colors.text,
    fontSize: 20,
    fontWeight: "800",
    letterSpacing: -0.5,
  },
  gamePkg: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 11,
    marginTop: 4,
  },
  toggleChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderWidth: 1,
    borderRadius: 3,
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  toggleText: {
    fontFamily: mono,
    fontSize: 10,
    letterSpacing: 1.5,
    fontWeight: "700",
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  metaCell: { flex: 1 },
  metaLabel: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 9,
    letterSpacing: 1.5,
    marginBottom: 2,
  },
  metaValue: {
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
  codeBlock: {
    backgroundColor: colors.surfaceDeep,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 3,
    padding: 12,
  },
  codeText: {
    fontFamily: mono,
    color: colors.accent,
    fontSize: 11,
    lineHeight: 18,
  },
  milestoneHeader: { marginTop: 24, marginBottom: 8 },
  milestone: { flexDirection: "row", gap: 12, marginBottom: 8 },
  checkbox: {
    width: 20,
    height: 20,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 3,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 2,
  },
  mLabel: { fontFamily: mono, color: colors.text, fontSize: 13, fontWeight: "700" },
  mDesc: {
    fontFamily: mono,
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 4,
  },
  mMetaRow: { flexDirection: "row", gap: 6, marginTop: 8 },
  mMeta: { fontFamily: mono, color: colors.textTertiary, fontSize: 10 },
  emptyText: {
    color: colors.textSecondary,
    fontFamily: mono,
    fontSize: 12,
    textAlign: "center",
  },
});
