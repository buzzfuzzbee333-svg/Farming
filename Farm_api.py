#!/usr/bin/env python3
"""
farm_api.py — Local HTTP API for the Idle Farmer
Runs in Termux. Emergent web app + Power Automate call this.

Endpoints:
  GET  /status          — current session state
  GET  /games           — list available game configs
  POST /start           — start a farm session
  POST /stop            — kill any running session
  GET  /sessions        — recent sessions from Supabase
"""

import json
import os
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Config ──────────────────────────────────────────────────
PORT = 8765
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(SCRIPT_DIR, "..", "configs")
SESSION_FILE = "/tmp/current_farm_session.txt"

# Load .env
env_path = os.path.join(SCRIPT_DIR, "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


# ── Supabase helper ─────────────────────────────────────────
def supa_get(path):
    if not SUPABASE_URL:
        return []
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


# ── Game config helpers ─────────────────────────────────────
def list_game_configs():
    games = []
    if not os.path.isdir(CONFIGS_DIR):
        return games
    for fname in sorted(os.listdir(CONFIGS_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(CONFIGS_DIR, fname)
        try:
            with open(fpath) as f:
                cfg = json.load(f)
            games.append({
                "file": fname,
                "name": cfg.get("name", fname),
                "package": cfg.get("package_name"),
                "session_minutes": cfg.get("loop", {}).get("session_minutes"),
                "collect_interval_ms": cfg.get("loop", {}).get("collect_interval_ms"),
                "upgrade_interval_ms": cfg.get("loop", {}).get("upgrade_interval_ms"),
            })
        except Exception:
            pass
    return games


def current_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            sid = f.read().strip()
        return {"status": "running", "session_id": sid}
    return {"status": "idle"}


# ── Request handler ─────────────────────────────────────────
class FarmHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/status":
            self._ok(current_session())

        elif path == "/games":
            self._ok(list_game_configs())

        elif path == "/sessions":
            data = supa_get(
                "idle_sessions?select=id,started_at,ended_at,status,earned_cents,"
                "idle_games(name)&order=started_at.desc&limit=20"
            )
            self._ok(data)

        elif path == "/health":
            self._ok({"ok": True, "ts": datetime.utcnow().isoformat()})

        else:
            self._err(404, "Not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length))
            except Exception:
                self._err(400, "Invalid JSON body")
                return

        if path == "/start":
            sess = current_session()
            if sess["status"] == "running":
                self._err(409, f"Already running session {sess['session_id']}")
                return

            config_file = body.get("config_file")
            minutes = body.get("minutes")

            if not config_file:
                self._err(400, "config_file is required (e.g. 'idle-bank-tycoon.json')")
                return

            config_path = os.path.join(CONFIGS_DIR, config_file)
            if not os.path.exists(config_path):
                self._err(404, f"Config not found: {config_file}")
                return

            hub = os.path.join(SCRIPT_DIR, "farm_hub.sh")
            cmd = ["bash", hub, config_path]
            if minutes:
                cmd.append(str(int(minutes)))

            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._ok({"status": "started", "game": config_file, "minutes": minutes})

        elif path == "/stop":
            os.system("pkill -f idle_runner.sh 2>/dev/null; pkill -f farm_hub.sh 2>/dev/null")
            self._ok({"status": "stopped"})

        else:
            self._err(404, "Not found")

    def do_OPTIONS(self):
        # Allow CORS preflight from Emergent app
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _ok(self, data):
        self._respond(200, data)

    def _err(self, code, msg):
        self._respond(code, {"error": msg})

    def _respond(self, code, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}")


# ── Main ────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🌾 Farm API → http://localhost:{PORT}")
    print(f"   Configs : {CONFIGS_DIR}")
    print(f"   Supabase: {'✅ configured' if SUPABASE_URL else '⚠️  not set (add to .env)'}")
    print()
    HTTPServer(("0.0.0.0", PORT), FarmHandler).serve_forever()

