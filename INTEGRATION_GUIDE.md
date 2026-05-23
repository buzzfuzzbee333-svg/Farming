# Idle Game Automation — Integration Guide

Wire your **Automate (LlamaLab)**, **Termux**, or **n8n** pipeline to the mobile control app so every farm run is logged automatically.

---

## Base URL

```
https://miner-farm.preview.emergentagent.com
```

(After you deploy via Emergent's Publish button, replace with your production URL.)

All endpoints are prefixed with `/api`.

---

## The 2-endpoint integration (simplest path)

You only need **two** HTTP calls in your Automate flow / Termux script to get full session logging in the dashboard.

### 1. At session start

```bash
curl -X POST https://miner-farm.preview.emergentagent.com/api/sessions/start_by_pkg \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "com.cryptominer.tycoon",
    "session_minutes": 60,
    "notes": "n8n auto-rotation #4"
  }'
```

**Response** (save `id` for the next call):
```json
{
  "id": "fa7cc5e4-...",
  "game_id": "5cfa8562-...",
  "game_name": "Crypto Miner Tycoon",
  "session_minutes": 60,
  "started_at": "2026-05-22T21:15:04Z",
  "status": "running",
  "earned_cents": 0
}
```

### 2. At session end

```bash
curl -X POST https://miner-farm.preview.emergentagent.com/api/sessions/{SESSION_ID}/complete \
  -H "Content-Type: application/json" \
  -d '{
    "earned_cents": 500,
    "status": "completed",
    "notes": "Reached daily VIP"
  }'
```

`status` can be `completed`, `failed`, or `aborted`.

---

## Updated Automate flow (with HTTP callbacks)

Add these two **HTTP Request** blocks to your existing Crypto Miner Tycoon flow:

### Block A — right after `Init Timers` (node id 18), before the main loop

```json
{
  "id": 100,
  "type": "http_request",
  "name": "Log Session Start",
  "method": "POST",
  "url": "https://miner-farm.preview.emergentagent.com/api/sessions/start_by_pkg",
  "headers": { "Content-Type": "application/json" },
  "body": "{\"package_name\":\"${pkg}\",\"session_minutes\":${session_minutes},\"notes\":\"Automate flow\"}",
  "save_response_to": "session_response"
}
```

Then add a `variables_set` block to capture the session id:
```json
{
  "id": 101,
  "type": "variables_set",
  "name": "Save Session ID",
  "variables": {
    "session_id": "${json(session_response).id}"
  }
}
```

### Block B — right before `End Session` (node id 17)

```json
{
  "id": 102,
  "type": "http_request",
  "name": "Log Session Complete",
  "method": "POST",
  "url": "https://miner-farm.preview.emergentagent.com/api/sessions/${session_id}/complete",
  "headers": { "Content-Type": "application/json" },
  "body": "{\"earned_cents\":0,\"status\":\"completed\"}"
}
```

Update `earned_cents` if your flow can read it from the game (OCR, screenshot diff, etc).

---

## Termux shell wrapper (drop-in replacement for `idle_runner.sh`)

Save as `~/idle_runner_logged.sh`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
set -e

GAME_CONFIG="$1"
SESSION_MINUTES="${2:-45}"
BASE_URL="${IDLE_API_URL:-https://miner-farm.preview.emergentagent.com}"

if [ -z "$GAME_CONFIG" ]; then
  echo "Usage: idle_runner_logged.sh <config.json> [session_minutes]"
  exit 1
fi

PKG=$(jq -r '.package_name' "$GAME_CONFIG")
COLLECT_X=$(jq -r '.tap_regions.collect.x' "$GAME_CONFIG")
COLLECT_Y=$(jq -r '.tap_regions.collect.y' "$GAME_CONFIG")
COLLECT_MS=$(jq -r '.loop.collect_interval_ms' "$GAME_CONFIG")

# 1. LOG START -----------------------------------------------------------
SESSION_ID=$(curl -s -X POST "$BASE_URL/api/sessions/start_by_pkg" \
  -H "Content-Type: application/json" \
  -d "{\"package_name\":\"$PKG\",\"session_minutes\":$SESSION_MINUTES,\"notes\":\"termux run\"}" \
  | jq -r '.id')

echo "▶ Session started: $SESSION_ID"

# trap so we still log on Ctrl+C / kill
finalize() {
  STATUS="${1:-aborted}"
  EARN="${2:-0}"
  curl -s -X POST "$BASE_URL/api/sessions/$SESSION_ID/complete" \
    -H "Content-Type: application/json" \
    -d "{\"earned_cents\":$EARN,\"status\":\"$STATUS\"}" > /dev/null
  echo "■ Session $STATUS"
}
trap 'finalize aborted 0' INT TERM

# 2. LAUNCH GAME ---------------------------------------------------------
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1
sleep 15

START_TS=$(date +%s)
while true; do
  NOW=$(date +%s)
  ELAPSED_MIN=$(( (NOW - START_TS) / 60 ))
  if [ "$ELAPSED_MIN" -ge "$SESSION_MINUTES" ]; then
    break
  fi
  adb shell input tap "$COLLECT_X" "$COLLECT_Y"
  sleep $(echo "scale=2; $COLLECT_MS/1000" | bc)
done

# 3. LOG COMPLETE --------------------------------------------------------
# Replace 0 with your earned amount in cents if you can detect it
finalize completed 0
```

Run it:
```bash
bash ~/idle_runner_logged.sh /sdcard/idle_configs/cryptominer_tycoon.json 60
```

---

## n8n workflow (for fire-and-forget rotation)

```
[Cron every 2h] 
   → [HTTP GET /api/games?active_only=true]
   → [Function: pick top by base_payout_cents / est_minutes]
   → [HTTP POST /api/sessions/start_by_pkg with picked game]
   → [Webhook to your Automate trigger on phone]
   → [Wait X minutes]
   → [HTTP POST /api/sessions/{id}/complete]
```

The Function node ranks games by ROI:
```javascript
return items
  .map(i => ({ ...i.json, roi: i.json.base_payout_cents / Math.max(1, i.json.est_minutes) }))
  .sort((a, b) => b.roi - a.roi)
  .slice(0, 1)
  .map(json => ({ json }));
```

---

## Full endpoint reference (everything you can call)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/dashboard` | Aggregate stats + recent sessions |
| `GET` | `/api/games?active_only=true` | List games (filterable) |
| `GET` | `/api/games/{id}` | Single game with `config_json` + `automate_flow_json` |
| `POST` | `/api/games` | Add a new game |
| `PATCH` | `/api/games/{id}` | Update game fields |
| `DELETE` | `/api/games/{id}` | Delete + cascade sessions/milestones |
| `POST` | `/api/sessions` | Start session by `game_id` (needs UUID) |
| `POST` | **`/api/sessions/start_by_pkg`** | Start session by `package_name` (recommended) |
| `GET` | `/api/sessions?status=running&game_id=...` | List/filter sessions |
| `PATCH` | `/api/sessions/{id}` | Update session fields |
| `POST` | **`/api/sessions/{id}/complete`** | Finalize session (one-shot) |
| `POST` | `/api/sessions/{id}/stop` | Mark as aborted |
| `GET` | `/api/milestones?game_id=...` | List milestones for a game |
| `POST` | `/api/milestones` | Add milestone |
| `PATCH` | `/api/milestones/{id}` | Update / toggle complete |
| `DELETE` | `/api/milestones/{id}` | Remove milestone |

---

## Quick test commands

```bash
# 1. Verify the API is alive
curl https://miner-farm.preview.emergentagent.com/api/

# 2. List your games
curl https://miner-farm.preview.emergentagent.com/api/games | jq '.[] | {name, package_name}'

# 3. Start a fake 1-minute session for Crypto Miner Tycoon
SID=$(curl -s -X POST https://miner-farm.preview.emergentagent.com/api/sessions/start_by_pkg \
  -H "Content-Type: application/json" \
  -d '{"package_name":"com.cryptominer.tycoon","session_minutes":1}' | jq -r '.id')
echo "Started session: $SID"

# 4. Complete it with $5.00 earnings
curl -s -X POST "https://miner-farm.preview.emergentagent.com/api/sessions/$SID/complete" \
  -H "Content-Type: application/json" \
  -d '{"earned_cents":500,"status":"completed"}' | jq

# 5. Confirm it shows in the dashboard
curl -s https://miner-farm.preview.emergentagent.com/api/dashboard | jq '{earnings: .total_earnings_cents, completed: .completed_sessions}'
```

Open the **Dashboard** tab in the app — total earnings should now show **$5.00**. 🎉
