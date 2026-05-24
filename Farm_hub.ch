#!/usr/bin/env bash
# farm_hub.sh — Wraps idle_runner.sh with Supabase logging
# Usage: bash farm_hub.sh <config.json> [session_minutes]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

# ── Load .env ──────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

: "${SUPABASE_URL:?Set SUPABASE_URL in .env}"
: "${SUPABASE_ANON_KEY:?Set SUPABASE_ANON_KEY in .env}"

GAME_CONFIG="${1:-}"
SESSION_MINUTES_OVERRIDE="${2:-}"

if [[ -z "$GAME_CONFIG" ]]; then
  echo "Usage: farm_hub.sh <config.json> [session_minutes]"
  exit 1
fi

if [[ ! -f "$GAME_CONFIG" ]]; then
  echo "❌ Config not found: $GAME_CONFIG"
  exit 1
fi

# ── Read game identity from config ─────────────────────────
GAME_NAME="$(jq -r '.name' "$GAME_CONFIG")"
PKG="$(jq -r '.package_name' "$GAME_CONFIG")"
echo "🌾 Starting farm: $GAME_NAME ($PKG)"

# ── Look up game_id in Supabase ────────────────────────────
SUPA_AUTH=(-H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY")

GAME_RESP=$(curl -sf \
  "${SUPA_AUTH[@]}" \
  "${SUPABASE_URL}/rest/v1/idle_games?package_name=eq.${PKG}&is_active=eq.true&select=id,base_payout_cents")

GAME_ID="$(echo "$GAME_RESP" | jq -r '.[0].id')"
BASE_PAYOUT="$(echo "$GAME_RESP" | jq -r '.[0].base_payout_cents // 0')"

if [[ "$GAME_ID" == "null" || -z "$GAME_ID" ]]; then
  echo "⚠️  Game not in Supabase. Run this once to insert it:"
  echo ""
  echo "  INSERT INTO idle_games (name, package_name, base_payout_cents, est_minutes, config_json)"
  echo "  VALUES ('$GAME_NAME', '$PKG', 0, 45, '$(cat "$GAME_CONFIG")'::jsonb);"
  echo ""
  exit 1
fi
echo "✅ game_id: $GAME_ID  base_payout: ${BASE_PAYOUT}¢"

# ── Create session ─────────────────────────────────────────
SESSION_RESP=$(curl -sf -X POST \
  "${SUPA_AUTH[@]}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d "{\"game_id\":\"$GAME_ID\",\"status\":\"running\"}" \
  "${SUPABASE_URL}/rest/v1/idle_sessions")

SESSION_ID="$(echo "$SESSION_RESP" | jq -r '.[0].id')"
echo "📝 Session ID: $SESSION_ID"
echo "$SESSION_ID" > /tmp/current_farm_session.txt

# ── Trap: mark session failed if script is killed ──────────
_cleanup() {
  local exit_code=$?
  local final_status="failed"
  [[ $exit_code -eq 0 ]] && final_status="completed"
  echo "🔚 Closing session as: $final_status"
  curl -sf -X PATCH \
    "${SUPA_AUTH[@]}" \
    -H "Content-Type: application/json" \
    -d "{
      \"status\":\"$final_status\",
      \"ended_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"earned_cents\":$BASE_PAYOUT
    }" \
    "${SUPABASE_URL}/rest/v1/idle_sessions?id=eq.${SESSION_ID}" >/dev/null
  rm -f /tmp/current_farm_session.txt
}
trap _cleanup EXIT

# ── Run the game ───────────────────────────────────────────
RUNNER="${SCRIPT_DIR}/idle_runner.sh"

if [[ -n "$SESSION_MINUTES_OVERRIDE" ]]; then
  bash "$RUNNER" "$GAME_CONFIG" "$SESSION_MINUTES_OVERRIDE"
else
  bash "$RUNNER" "$GAME_CONFIG"
fi

echo "✅ Farm session complete."

