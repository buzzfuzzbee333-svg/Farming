#!/usr/bin/env bash
set -euo pipefail

GAME_CONFIG="${1:-}"
SESSION_MINUTES_OVERRIDE="${2:-}"

if [[ -z "$GAME_CONFIG" ]]; then
  echo "Usage: idle_runner.sh <config.json> [session_minutes]"
  exit 1
fi

if [[ ! -f "$GAME_CONFIG" ]]; then
  echo "Config not found: $GAME_CONFIG"
  exit 1
fi

for cmd in jq adb bc; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing dependency: $cmd"
    exit 1
  fi
done

PKG="$(jq -r '.package_name' "$GAME_CONFIG")"
COLLECT_X="$(jq -r '.tap_regions.collect.x' "$GAME_CONFIG")"
COLLECT_Y="$(jq -r '.tap_regions.collect.y' "$GAME_CONFIG")"
UP1_X="$(jq -r '.tap_regions.upgrade_1.x' "$GAME_CONFIG")"
UP1_Y="$(jq -r '.tap_regions.upgrade_1.y' "$GAME_CONFIG")"
UP2_X="$(jq -r '.tap_regions.upgrade_2.x' "$GAME_CONFIG")"
UP2_Y="$(jq -r '.tap_regions.upgrade_2.y' "$GAME_CONFIG")"
UP3_X="$(jq -r '.tap_regions.upgrade_3.x' "$GAME_CONFIG")"
UP3_Y="$(jq -r '.tap_regions.upgrade_3.y' "$GAME_CONFIG")"

COLLECT_MS="$(jq -r '.loop.collect_interval_ms' "$GAME_CONFIG")"
UPGRADE_MS="$(jq -r '.loop.upgrade_interval_ms' "$GAME_CONFIG")"
CFG_SESSION_MINUTES="$(jq -r '.loop.session_minutes' "$GAME_CONFIG")"

SESSION_MINUTES="$CFG_SESSION_MINUTES"
if [[ -n "$SESSION_MINUTES_OVERRIDE" && "$SESSION_MINUTES_OVERRIDE" != "null" ]]; then
  SESSION_MINUTES="$SESSION_MINUTES_OVERRIDE"
fi

adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1
sleep 15

START_TS="$(date +%s)"
NEXT_UPGRADE_TS="$((START_TS + UPGRADE_MS / 1000))"

while true; do
  NOW="$(date +%s)"
  ELAPSED_MINUTES="$(((NOW - START_TS) / 60))"
  if [[ "$ELAPSED_MINUTES" -ge "$SESSION_MINUTES" ]]; then
    echo "Session complete (${ELAPSED_MINUTES} min)."
    break
  fi

  adb shell input tap "$COLLECT_X" "$COLLECT_Y"

  if [[ "$NOW" -ge "$NEXT_UPGRADE_TS" ]]; then
    adb shell input tap "$UP1_X" "$UP1_Y"
    adb shell input tap "$UP2_X" "$UP2_Y"
    adb shell input tap "$UP3_X" "$UP3_Y"
    NEXT_UPGRADE_TS="$((NOW + UPGRADE_MS / 1000))"
  fi

  sleep "$(echo "scale=2; $COLLECT_MS/1000" | bc)"
done
