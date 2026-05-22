import { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { api, IdleSession } from "@/src/lib/api";
import { colors, mono, formatUSD } from "@/src/lib/theme";
import { Card, Badge, SectionLabel, PrimaryButton } from "@/src/components/ui";

const FILTERS = ["all", "running", "completed", "failed", "aborted"] as const;
type Filter = (typeof FILTERS)[number];

export default function SessionsScreen() {
  const router = useRouter();
  const [sessions, setSessions] = useState<IdleSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");

  const load = useCallback(async () => {
    try {
      const params: any = {};
      if (filter !== "all") params.status = filter;
      const s = await api.listSessions(params);
      setSessions(s);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleStop = (s: IdleSession) => {
    Alert.alert("Abort session?", `Mark ${s.game_name} as aborted.`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Abort",
        style: "destructive",
        onPress: async () => {
          await api.stopSession(s.id);
          load();
        },
      },
    ]);
  };

  const handleComplete = (s: IdleSession) => {
    Alert.prompt?.("Earnings (cents)", "Enter earned amount in cents:", async (val) => {
      const cents = parseInt(val || "0", 10) || 0;
      await api.updateSession(s.id, { status: "completed", earned_cents: cents });
      load();
    });
    // Fallback if Alert.prompt unavailable (Android): mark with 0
    if (!(Alert as any).prompt) {
      api
        .updateSession(s.id, { status: "completed", earned_cents: 0 })
        .then(load);
    }
  };

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
      testID="sessions-screen"
    >
      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f}
            onPress={() => setFilter(f)}
            style={[
              styles.filterChip,
              filter === f && styles.filterChipActive,
            ]}
            testID={`filter-${f}`}
            activeOpacity={0.7}
          >
            <Text
              style={[
                styles.filterChipText,
                filter === f && { color: colors.accent },
              ]}
            >
              {f.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <SectionLabel style={{ marginBottom: 8 }}>
        // LOG [{sessions.length}]
      </SectionLabel>

      {sessions.length === 0 ? (
        <Card>
          <Text style={styles.emptyText}>No sessions match this filter.</Text>
          <PrimaryButton
            label="▶ Start New Session"
            onPress={() => router.push("/session/new")}
            testID="empty-start-btn"
            style={{ marginTop: 12 }}
          />
        </Card>
      ) : (
        sessions.map((s) => (
          <Card key={s.id} style={styles.sessionCard} testID={`session-card-${s.id}`}>
            <View style={styles.topRow}>
              <Text style={styles.gameName} numberOfLines={1}>
                {s.game_name || "—"}
              </Text>
              <Badge status={s.status} />
            </View>
            <View style={styles.metaGrid}>
              <View style={styles.metaCell}>
                <Text style={styles.metaLabel}>STARTED</Text>
                <Text style={styles.metaValue}>
                  {new Date(s.started_at).toLocaleString()}
                </Text>
              </View>
              <View style={styles.metaCell}>
                <Text style={styles.metaLabel}>DURATION</Text>
                <Text style={styles.metaValue}>{s.session_minutes}m</Text>
              </View>
              <View style={styles.metaCell}>
                <Text style={styles.metaLabel}>EARNED</Text>
                <Text style={[styles.metaValue, { color: colors.accent }]}>
                  {formatUSD(s.earned_cents)}
                </Text>
              </View>
            </View>
            {!!s.notes && (
              <Text style={styles.notes} numberOfLines={2}>
                # {s.notes}
              </Text>
            )}
            {s.status === "running" && (
              <View style={styles.actions}>
                <TouchableOpacity
                  onPress={() => handleComplete(s)}
                  style={[styles.actionBtn, { borderColor: colors.accentBorder }]}
                  testID={`complete-${s.id}`}
                  activeOpacity={0.7}
                >
                  <Ionicons name="checkmark" size={14} color={colors.accent} />
                  <Text style={[styles.actionText, { color: colors.accent }]}>
                    COMPLETE
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => handleStop(s)}
                  style={[styles.actionBtn, { borderColor: colors.redBorder }]}
                  testID={`abort-${s.id}`}
                  activeOpacity={0.7}
                >
                  <Ionicons name="stop" size={14} color={colors.red} />
                  <Text style={[styles.actionText, { color: colors.red }]}>
                    ABORT
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </Card>
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
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginBottom: 16,
  },
  filterChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  filterChipActive: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accentBorder,
  },
  filterChipText: {
    fontFamily: mono,
    fontSize: 10,
    letterSpacing: 1.5,
    color: colors.textTertiary,
    fontWeight: "700",
  },
  emptyText: {
    color: colors.textSecondary,
    fontFamily: mono,
    fontSize: 12,
    textAlign: "center",
  },
  sessionCard: { marginBottom: 10 },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  gameName: {
    fontFamily: mono,
    color: colors.text,
    fontSize: 14,
    fontWeight: "700",
    flex: 1,
    marginRight: 8,
  },
  metaGrid: { flexDirection: "row", gap: 12 },
  metaCell: { flex: 1 },
  metaLabel: {
    fontFamily: mono,
    fontSize: 9,
    color: colors.textTertiary,
    letterSpacing: 1.5,
    marginBottom: 2,
  },
  metaValue: { fontFamily: mono, fontSize: 11, color: colors.text },
  notes: {
    fontFamily: mono,
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 10,
    fontStyle: "italic",
  },
  actions: { flexDirection: "row", gap: 8, marginTop: 12 },
  actionBtn: {
    flex: 1,
    flexDirection: "row",
    gap: 6,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 8,
    borderRadius: 3,
    borderWidth: 1,
    backgroundColor: colors.surface2,
  },
  actionText: {
    fontFamily: mono,
    fontSize: 10,
    letterSpacing: 1.5,
    fontWeight: "700",
  },
});
