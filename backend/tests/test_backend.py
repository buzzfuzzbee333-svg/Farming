"""Backend API tests for Idle Game Automation Stack."""
import os
import pytest
import requests
from pathlib import Path

# Load EXPO_PUBLIC_BACKEND_URL from frontend/.env
env_path = Path(__file__).resolve().parents[2] / "frontend" / ".env"
BASE_URL = None
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
            break
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL missing"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def games(client):
    r = client.get(f"{API}/games", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    return data


# ===== Root & Dashboard =====
def test_root(client):
    r = client.get(f"{API}/", timeout=20)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_dashboard(client):
    r = client.get(f"{API}/dashboard", timeout=20)
    assert r.status_code == 200
    d = r.json()
    for k in ["total_earnings_cents", "active_sessions", "completed_sessions",
              "failed_sessions", "total_runtime_minutes", "total_games", "recent_sessions"]:
        assert k in d, f"missing {k}"
    assert isinstance(d["recent_sessions"], list)
    assert d["total_games"] >= 2


# ===== Games =====
def test_games_seeded(games):
    names = [g["name"] for g in games]
    assert "Idle Bank Tycoon" in names
    assert "Crypto Miner Tycoon" in names
    for g in games:
        assert "_id" not in g
        assert "id" in g and "config_json" in g


def test_get_game_by_id(client, games):
    gid = games[0]["id"]
    r = client.get(f"{API}/games/{gid}")
    assert r.status_code == 200
    assert r.json()["id"] == gid


def test_get_game_404(client):
    r = client.get(f"{API}/games/nope-xyz")
    assert r.status_code == 404


def test_game_crud_cycle(client):
    # Create
    payload = {
        "name": "TEST_Game_AutoTest",
        "package_name": "com.test.autotest",
        "base_payout_cents": 100,
        "est_minutes": 10,
        "config_json": {"name": "x", "package_name": "com.test.autotest",
                        "tap_regions": {"collect": {"x": 1, "y": 2}},
                        "loop": {"collect_interval_ms": 1000},
                        "safety": {"max_runtime_minutes": 30}},
        "is_active": True,
    }
    r = client.post(f"{API}/games", json=payload)
    assert r.status_code == 200, r.text
    gid = r.json()["id"]

    # Patch toggle
    r = client.patch(f"{API}/games/{gid}", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # Verify via GET
    r = client.get(f"{API}/games/{gid}")
    assert r.json()["is_active"] is False

    # Create milestone + session under this game to test cascade
    ms = client.post(f"{API}/milestones", json={
        "game_id": gid, "label": "TEST_MS", "target_desc": "x",
        "est_minutes": 5, "payout_cents": 50, "order_index": 1
    })
    assert ms.status_code == 200
    sess = client.post(f"{API}/sessions", json={"game_id": gid, "session_minutes": 15})
    assert sess.status_code == 200
    sid = sess.json()["id"]

    # Delete cascades
    r = client.delete(f"{API}/games/{gid}")
    assert r.status_code == 200 and r.json()["deleted"] is True

    r = client.get(f"{API}/games/{gid}")
    assert r.status_code == 404
    r = client.get(f"{API}/sessions/{sid}")
    assert r.status_code == 404


# ===== Sessions =====
def test_session_lifecycle(client, games):
    gid = games[0]["id"]
    gname = games[0]["name"]
    r = client.post(f"{API}/sessions", json={"game_id": gid, "session_minutes": 30,
                                              "notes": "TEST_pytest"})
    assert r.status_code == 200, r.text
    sess = r.json()
    assert sess["game_name"] == gname
    assert sess["status"] == "running"
    sid = sess["id"]

    # Filter by status=running
    r = client.get(f"{API}/sessions", params={"status": "running"})
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    # Filter by game_id
    r = client.get(f"{API}/sessions", params={"game_id": gid})
    assert any(s["id"] == sid for s in r.json())

    # PATCH to completed sets ended_at
    r = client.patch(f"{API}/sessions/{sid}", json={"status": "completed", "earned_cents": 250})
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "completed"
    assert j["ended_at"] is not None
    assert j["earned_cents"] == 250

    # cleanup
    client.delete(f"{API}/sessions/{sid}")


def test_session_stop(client, games):
    gid = games[1]["id"]
    r = client.post(f"{API}/sessions", json={"game_id": gid, "session_minutes": 20})
    sid = r.json()["id"]
    r = client.post(f"{API}/sessions/{sid}/stop")
    assert r.status_code == 200
    assert r.json()["status"] == "aborted"
    assert r.json()["ended_at"] is not None
    client.delete(f"{API}/sessions/{sid}")


def test_session_invalid_game(client):
    r = client.post(f"{API}/sessions", json={"game_id": "nope", "session_minutes": 10})
    assert r.status_code == 404


# ===== Milestones =====
def test_milestones_listing_ordered(client, games):
    gid = games[0]["id"]
    r = client.get(f"{API}/milestones", params={"game_id": gid})
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 3
    orders = [m["order_index"] for m in data]
    assert orders == sorted(orders)


def test_milestone_crud(client, games):
    gid = games[0]["id"]
    r = client.post(f"{API}/milestones", json={
        "game_id": gid, "label": "TEST_milestone", "target_desc": "tmp",
        "est_minutes": 5, "payout_cents": 10, "order_index": 99
    })
    assert r.status_code == 200
    mid = r.json()["id"]
    r = client.patch(f"{API}/milestones/{mid}", json={"completed": True})
    assert r.status_code == 200 and r.json()["completed"] is True
    r = client.delete(f"{API}/milestones/{mid}")
    assert r.status_code == 200


# ===== Dashboard aggregation =====
def test_dashboard_aggregation(client, games):
    gid = games[0]["id"]
    s = client.post(f"{API}/sessions", json={"game_id": gid, "session_minutes": 25}).json()
    sid = s["id"]
    client.patch(f"{API}/sessions/{sid}", json={"status": "completed", "earned_cents": 777})
    d = client.get(f"{API}/dashboard").json()
    assert d["total_earnings_cents"] >= 777
    assert d["total_runtime_minutes"] >= 25
    assert d["completed_sessions"] >= 1
    client.delete(f"{API}/sessions/{sid}")
