import { useEffect, useState, useCallback } from "react";
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
import { api, DashboardStats } from "@/src/lib/api";
import { colors, mono, formatUSD, formatMinutes } from "@/src/lib/theme";
import { Card, Badge, StatBlock, SectionLabel, PrimaryButton } from "@/src/components/ui";

export default function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const d = await api.dashboard();
      setData(d);
    } catch (e: any) {
      setError(e.message || "Failed to load");
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

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <View style={styles.loading} testID="dashboard-loading">
        <ActivityIndicator color={colors.accent} />
        <Text style={styles.loadingText}>BOOTING_</Text>
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
      testID="dashboard-screen"
    >
      {error && (
        <Card style={{ borderColor: colors.redBorder, marginBottom: 16 }}>
          <Text style={{ color: colors.red, fontFamily: mono, fontSize: 12 }}>
            ERR: {error}
          </Text>
        </Card>
      )}

      {/* Earnings Hero */}
      <Card style={styles.heroCard} testID="dashboard-earnings">
        <View style={styles.heroTopRow}>
          <Text style={styles.heroLabel}>TOTAL_EARNINGS</Text>
          <View style={styles.live}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>LIVE</Text>
          </View>
        </View>
        <Text style={styles.heroValue} adjustsFontSizeToFit numberOfLines={1}>
          {formatUSD(data?.total_earnings_cents ?? 0)}
        </Text>
        <Text style={styles.heroSub}>
          across {data?.completed_sessions ?? 0} completed runs
        </Text>
      </Card>

      {/* Stats grid */}
      <View style={styles.statsRow}>
        <StatBlock
          label="Active"
          value={String(data?.active_sessions ?? 0)}
          accent={(data?.active_sessions ?? 0) > 0}
          testID="stat-active"
        />
        <StatBlock
          label="Runtime"
          value={formatMinutes(data?.total_runtime_minutes ?? 0)}
          testID="stat-runtime"
        />
        <StatBlock
          label="Games"
          value={String(data?.total_games ?? 0)}
          testID="stat-games"
        />
      </View>

      {/* Quick start */}
      <PrimaryButton
        label="▶  Start New Session"
        onPress={() => router.push("/session/new")}
        testID="start-session-btn"
        style={{ marginTop: 16 }}
      />

      {/* Recent sessions */}
      <SectionLabel style={{ marginTop: 28, marginBottom: 12 }}>
        // RECENT_SESSIONS
      </SectionLabel>

      {(!data?.recent_sessions || data.recent_sessions.length === 0) ? (
        <Card>
          <Text style={styles.emptyText}>
            No sessions yet. Start one to see logs here.
          </Text>
        </Card>
      ) : (
        data.recent_sessions.map((s) => (
          <TouchableOpacity
            key={s.id}
            activeOpacity={0.7}
            onPress={() => router.push(`/game/${s.game_id}`)}
            testID={`session-row-${s.id}`}
          >
            <Card style={styles.sessionRow}>
              <View style={{ flex: 1 }}>
                <View style={styles.sessionTopRow}>
                  <Text style={styles.sessionGame} numberOfLines={1}>
                    {s.game_name || "Unknown"}
                  </Text>
                  <Badge status={s.status} testID={`session-status-${s.id}`} />
                </View>
                <View style={styles.sessionMetaRow}>
                  <Text style={styles.sessionMeta}>
                    {new Date(s.started_at).toLocaleString()}
                  </Text>
                  <Text style={styles.sessionMeta}>·</Text>
                  <Text style={styles.sessionMeta}>{s.session_minutes}m</Text>
                  <Text style={styles.sessionMeta}>·</Text>
                  <Text style={[styles.sessionMeta, { color: colors.accent }]}>
                    {formatUSD(s.earned_cents)}
                  </Text>
                </View>
              </View>
              <Ionicons
                name="chevron-forward"
                size={18}
                color={colors.textTertiary}
              />
            </Card>
          </TouchableOpacity>
        ))
      )}

      <View style={{ height: 24 }} />
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
    gap: 12,
  },
  loadingText: {
    color: colors.textTertiary,
    fontFamily: mono,
    fontSize: 11,
    letterSpacing: 3,
  },
  heroCard: {
    paddingVertical: 24,
    backgroundColor: "#0d0f0c",
    borderColor: "rgba(34,197,94,0.18)",
  },
  heroTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  heroLabel: {
    fontFamily: mono,
    fontSize: 10,
    letterSpacing: 3,
    color: colors.textTertiary,
  },
  live: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderWidth: 1,
    borderColor: colors.accentBorder,
    backgroundColor: colors.accentSoft,
    borderRadius: 3,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.accent,
  },
  liveText: {
    fontFamily: mono,
    color: colors.accent,
    fontSize: 9,
    letterSpacing: 2,
  },
  heroValue: {
    fontFamily: mono,
    color: colors.accent,
    fontSize: 48,
    fontWeight: "800",
    letterSpacing: -1.5,
  },
  heroSub: {
    fontFamily: mono,
    color: colors.textTertiary,
    fontSize: 11,
    marginTop: 4,
    letterSpacing: 0.5,
  },
  statsRow: { flexDirection: "row", gap: 8, marginTop: 12 },
  sessionRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
    padding: 12,
  },
  sessionTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  sessionGame: {
    fontFamily: mono,
    color: colors.text,
    fontSize: 13,
    fontWeight: "700",
    flex: 1,
    marginRight: 8,
  },
  sessionMetaRow: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  sessionMeta: {
    fontFamily: mono,
    fontSize: 10,
    color: colors.textTertiary,
  },
  emptyText: {
    color: colors.textSecondary,
    fontFamily: mono,
    fontSize: 12,
    textAlign: "center",
    paddingVertical: 16,
  },
});
