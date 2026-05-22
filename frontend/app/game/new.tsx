import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useRouter } from "expo-router";
import { api } from "@/src/lib/api";
import { colors, mono } from "@/src/lib/theme";
import { PrimaryButton, SectionLabel } from "@/src/components/ui";

const DEFAULT_CONFIG = `{
  "name": "My Idle Game",
  "package_name": "com.example.idle",
  "tap_regions": {
    "collect":   { "x": 540, "y": 1600 },
    "upgrade_1": { "x": 150, "y": 1800 },
    "upgrade_2": { "x": 540, "y": 1800 },
    "upgrade_3": { "x": 930, "y": 1800 }
  },
  "loop": {
    "collect_interval_ms": 1500,
    "upgrade_interval_ms": 8000,
    "session_minutes": 45
  },
  "safety": {
    "restart_every_minutes": 15,
    "max_runtime_minutes": 60
  }
}`;

export default function NewGame() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [pkg, setPkg] = useState("");
  const [estMinutes, setEstMinutes] = useState("45");
  const [payoutCents, setPayoutCents] = useState("0");
  const [configText, setConfigText] = useState(DEFAULT_CONFIG);
  const [flowText, setFlowText] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!name.trim() || !pkg.trim()) {
      Alert.alert("Validation", "Name and package_name are required");
      return;
    }
    let parsed: any;
    try {
      parsed = JSON.parse(configText);
    } catch (e: any) {
      Alert.alert("Invalid JSON", `config_json: ${e.message}`);
      return;
    }
    let parsedFlow: any = null;
    if (flowText.trim()) {
      try {
        parsedFlow = JSON.parse(flowText);
      } catch (e: any) {
        Alert.alert("Invalid JSON", `automate_flow_json: ${e.message}`);
        return;
      }
    }
    setSaving(true);
    try {
      await api.createGame({
        name: name.trim(),
        package_name: pkg.trim(),
        est_minutes: parseInt(estMinutes || "0", 10) || 0,
        base_payout_cents: parseInt(payoutCents || "0", 10) || 0,
        config_json: parsed,
        automate_flow_json: parsedFlow,
        is_active: true,
      } as any);
      router.back();
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={{ flex: 1, backgroundColor: colors.bg }}
    >
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        testID="new-game-screen"
      >
        <SectionLabel>// NAME</SectionLabel>
        <TextInput
          value={name}
          onChangeText={setName}
          placeholder="Idle Bank Tycoon"
          placeholderTextColor={colors.textTertiary}
          style={styles.input}
          testID="input-name"
        />

        <SectionLabel style={{ marginTop: 16 }}>// PACKAGE_NAME</SectionLabel>
        <TextInput
          value={pkg}
          onChangeText={setPkg}
          placeholder="com.idlebank.tycoon"
          placeholderTextColor={colors.textTertiary}
          autoCapitalize="none"
          style={styles.input}
          testID="input-package"
        />

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <SectionLabel style={{ marginTop: 16 }}>// EST_MINUTES</SectionLabel>
            <TextInput
              value={estMinutes}
              onChangeText={setEstMinutes}
              keyboardType="number-pad"
              style={styles.input}
              testID="input-est-minutes"
            />
          </View>
          <View style={{ width: 12 }} />
          <View style={{ flex: 1 }}>
            <SectionLabel style={{ marginTop: 16 }}>// PAYOUT_CENTS</SectionLabel>
            <TextInput
              value={payoutCents}
              onChangeText={setPayoutCents}
              keyboardType="number-pad"
              style={styles.input}
              testID="input-payout"
            />
          </View>
        </View>

        <SectionLabel style={{ marginTop: 16 }}>// CONFIG_JSON</SectionLabel>
        <TextInput
          value={configText}
          onChangeText={setConfigText}
          multiline
          autoCapitalize="none"
          autoCorrect={false}
          style={[styles.input, styles.codeInput]}
          testID="input-config"
        />

        <SectionLabel style={{ marginTop: 16 }}>
          // AUTOMATE_FLOW_JSON (optional)
        </SectionLabel>
        <TextInput
          value={flowText}
          onChangeText={setFlowText}
          multiline
          autoCapitalize="none"
          autoCorrect={false}
          placeholder='Paste your Automate flow JSON here (or leave empty)'
          placeholderTextColor={colors.textTertiary}
          style={[styles.input, styles.codeInput, { minHeight: 200 }]}
          testID="input-flow"
        />

        <PrimaryButton
          label={saving ? "Saving..." : "Save Game"}
          onPress={save}
          disabled={saving}
          testID="save-game-btn"
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
  codeInput: {
    minHeight: 280,
    textAlignVertical: "top",
    fontSize: 11,
    color: colors.accent,
    backgroundColor: colors.surfaceDeep,
    lineHeight: 18,
  },
  row: { flexDirection: "row" },
});
