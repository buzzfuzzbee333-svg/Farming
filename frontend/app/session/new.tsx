import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, IdleGame } from "@/src/lib/api";
import { colors, mono, formatMinutes } from "@/src/lib/theme";
import { PrimaryButton, SectionLabel } from "@/src/components/ui";

const PRESET_MINUTES = [15, 30, 45, 60, 90];

export default function NewSession() {
  const params = useLocalSearchParams<{ game_id?: string }>();
  const router = useRouter();
  const [games, setGames] = useState<IdleGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedGameId, setSelectedGameId] = useState<string>(
    params.game_id || ""
  );
  const [minutes, setMinutes] = useState("45");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const g = await api.listGames();
      setGames(g);
      if (!selectedGameId && g.length > 0) {
        setSelectedGameId(g[0].id);
        setMinutes(String(g[0].est_minutes));
      } else if (selectedGameId) {
        const found = g.find((x) => x.id === selectedGameId);
        if (found) setMinutes(String(found.est_minutes));
      }
    } finally {
      setLoading(false);
    }
  }, [selectedGameId]);

  useEffect(() => {
    load();
  }, [load]);

  const start = async () => {
    if (!selectedGameId) {
      Alert.alert("Select game", "Pick a game first.");
      return;
    }
    const m = parseInt(minutes || "0", 10);
    if (!m || m < 1) {
      Alert.alert("Invalid minutes", "Enter a positive number.");
      return;
    }
    setSubmitting(true);
    try {
      await api.createSession({
        game_id: selectedGameId,
        session_minutes: m,
        notes: notes.trim() || undefined,
      });
      router.replace("/sessions");
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  if (games.length === 0) {
    return (
      <View style={styles.loading}>
        <Text style={styles.emptyText}>
          No games configured. Add a game first.
        </Text>
        <PrimaryButton
          label="+ Add Game"
          onPress={() => router.replace("/game/new")}
          testID="empty-add-game-btn"
          style={{ marginTop: 16 }}
        />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={{ flex: 1, backgroundColor: colors.bg }}
    >
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        testID="new-session-screen"
      >
        <SectionLabel>// SELECT_GAME</SectionLabel>
        <View style={{ gap: 8 }}>
          {games.map((g) => {
            const active = g.id === selectedGameId;
            return (
              <TouchableOpacity
                key={g.id}
                onPress={() => {
                  setSelectedGameId(g.id);
                  setMinutes(String(g.est_minutes));
                }}
                activeOpacity={0.7}
                style={[
                  styles.gameRow,
                  active && {
                    borderColor: colors.accentBorder,
                    backgroundColor: colors.accentSoft,
                  },
                ]}
                testID={`select-game-${g.id}`}
              >
                <View
                  style={[
                    styles.radio,
                    active && {
                      borderColor: colors.accent,
                    },
                  ]}
                >
                  {active && <View style={styles.radioDot} />}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.gameRowName}>{g.name}</Text>
                  <Text style={styles.gameRowPkg} numberOfLines={1}>
                    {g.package_name}
                  </Text>
                </View>
                <Text style={styles.gameRowMins}>
                  {formatMinutes(g.est_minutes)}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <SectionLabel style={{ marginTop: 24 }}>// SESSION_MINUTES</SectionLabel>
        <View style={styles.presetRow}>
          {PRESET_MINUTES.map((p) => (
            <TouchableOpacity
              key={p}
              onPress={() => setMinutes(String(p))}
              activeOpacity={0.7}
              style={[
                styles.preset,
                String(p) === minutes && {
                  backgroundColor: colors.accentSoft,
                  borderColor: colors.accentBorder,
                },
              ]}
              testID={`preset-${p}`}
            >
              <Text
                style={[
                  styles.presetText,
                  String(p) === minutes && { color: colors.accent },
                ]}
              >
                {p}m
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        <TextInput
          value={minutes}
          onChangeText={setMinutes}
          keyboardType="number-pad"
          style={styles.input}
          testID="input-minutes"
        />

        <SectionLabel style={{ marginTop: 16 }}>// NOTES (optional)</SectionLabel>
        <TextInput
          value={notes}
          onChangeText={setNotes}
          placeholder="e.g. Daily VIP push run"
          placeholderTextColor={colors.textTertiary}
          multiline
          style={[styles.input, { minHeight: 80, textAlignVertical: "top" }]}
          testID="input-notes"
        />

        <PrimaryButton
          label={submitting ? "Starting..." : "▶  Launch Session"}
          onPress={start}
          disabled={submitting}
          testID="launch-session-btn"
          style={{ marginTop: 24 }}
        />
        <View style={{ height: 64 }} />
      </ScrollView>
    </KeyboardAvoidingView>
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
    padding: 24,
  },
  emptyText: {
    color: colors.textSecondary,
    fontFamily: mono,
    fontSize: 13,
    textAlign: "center",
  },
  gameRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 3,
    backgroundColor: colors.surface,
  },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    borderColor: colors.border,
    justifyContent: "center",
    alignItems: "center",
  },
  radioDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.accent,
  },
  gameRowName: {
    fontFamily: mono,
    color: colors.text,
    fontSize: 13,
    fontWeight: "700",
  },
  gameRowPkg: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 10,
    marginTop: 2,
  },
  gameRowMins: {
    fontFamily: mono,
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
  },
  presetRow: {
    flexDirection: "row",
    gap: 6,
    marginBottom: 8,
  },
  preset: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  presetText: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: colors.surface2,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 3,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: colors.text,
    fontFamily: mono,
    fontSize: 13,
  },
});
