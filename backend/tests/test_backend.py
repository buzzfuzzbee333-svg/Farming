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


# ===== Iteration 2: automate_flow_json =====
def test_all_games_have_automate_flow_json(games):
    """Every game returned by /api/games must include an automate_flow_json object."""
    assert len(games) >= 2
    for g in games:
        assert "automate_flow_json" in g, f"missing automate_flow_json on {g['name']}"
        flow = g["automate_flow_json"]
        assert flow is not None and isinstance(flow, dict), f"flow is null on {g['name']}"
        assert "nodes" in flow and isinstance(flow["nodes"], list)
        assert "connections" in flow and isinstance(flow["connections"], list)
        assert "name" in flow


def test_crypto_miner_flow_has_18_nodes_and_correct_pkg(games):
    """Crypto Miner Tycoon flow: 18 nodes, pkg=com.cryptominer.tycoon."""
    cm = next((g for g in games if g["package_name"] == "com.cryptominer.tycoon"), None)
    assert cm is not None, "Crypto Miner Tycoon not in seed"
    flow = cm["automate_flow_json"]
    assert len(flow["nodes"]) == 18, f"expected 18 nodes got {len(flow['nodes'])}"
    # Node 1 = variables_set 'Load Config' must carry the pkg
    load_cfg = flow["nodes"][0]
    assert load_cfg["type"] == "variables_set"
    assert load_cfg["variables"]["pkg"] == "com.cryptominer.tycoon"
    assert load_cfg["variables"]["collect_x"] == 540
    assert load_cfg["variables"]["collect_y"] == 1650


def test_idle_bank_flow_templated_with_own_pkg_and_taps(games):
    """Idle Bank Tycoon must have been templated: same shape but pkg + tap coords swapped."""
    ib = next((g for g in games if g["package_name"] == "com.idlebank.tycoon"), None)
    assert ib is not None
    flow = ib["automate_flow_json"]
    assert flow is not None
    assert len(flow["nodes"]) == 18
    v = flow["nodes"][0]["variables"]
    assert v["pkg"] == "com.idlebank.tycoon"
    # Bank's tap_regions.collect = (540, 1600) from config_json
    assert v["collect_x"] == 540
    assert v["collect_y"] == 1600
    # restart_minutes from safety.restart_every_minutes = 15
    assert v["restart_minutes"] == 15
    assert v["session_minutes"] == 45
    # flow name should be game-specific
    assert "Idle Bank Tycoon" in flow["name"]


def test_create_game_with_automate_flow_json_roundtrip(client):
    """POST a game with automate_flow_json → GET it back → must be preserved verbatim."""
    custom_flow = {
        "name": "TEST_Flow",
        "description": "test flow",
        "version": 1,
        "nodes": [
            {"id": 1, "type": "variables_set", "variables": {"pkg": "com.test.flow"}},
            {"id": 2, "type": "shell_command", "command": "echo hi"},
        ],
        "connections": [{"from": 1, "to": 2}],
    }
    payload = {
        "name": "TEST_FlowGame",
        "package_name": "com.test.flow",
        "base_payout_cents": 0,
        "est_minutes": 5,
        "config_json": {"tap_regions": {}, "loop": {}, "safety": {}},
        "automate_flow_json": custom_flow,
        "is_active": True,
    }
    r = client.post(f"{API}/games", json=payload)
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    assert r.json()["automate_flow_json"] == custom_flow

    # Verify GET persists it
    r = client.get(f"{API}/games/{gid}")
    assert r.status_code == 200
    assert r.json()["automate_flow_json"] == custom_flow

    # cleanup
    client.delete(f"{API}/games/{gid}")


def test_create_game_without_automate_flow_json_is_null(client):
    """Optional field: POST without flow should yield null (then backfill won't run mid-test)."""
    payload = {
        "name": "TEST_NoFlowGame",
        "package_name": "com.test.noflow",
        "base_payout_cents": 0,
        "est_minutes": 5,
        "config_json": {"tap_regions": {}, "loop": {}, "safety": {}},
        "is_active": True,
    }
    r = client.post(f"{API}/games", json=payload)
    assert r.status_code == 200
    gid = r.json()["id"]
    assert r.json().get("automate_flow_json") is None
    client.delete(f"{API}/games/{gid}")


def test_patch_game_automate_flow_json(client):
    """PATCH /games/{id} must be able to update automate_flow_json."""
    create = client.post(f"{API}/games", json={
        "name": "TEST_PatchFlow",
        "package_name": "com.test.patchflow",
        "base_payout_cents": 0,
        "est_minutes": 5,
        "config_json": {"tap_regions": {}, "loop": {}, "safety": {}},
        "is_active": True,
    })
    gid = create.json()["id"]

    new_flow = {"name": "Updated", "nodes": [{"id": 1, "type": "delay"}], "connections": []}
    r = client.patch(f"{API}/games/{gid}", json={"automate_flow_json": new_flow})
    assert r.status_code == 200, r.text
    assert r.json()["automate_flow_json"] == new_flow

    # Verify via GET
    r = client.get(f"{API}/games/{gid}")
    assert r.json()["automate_flow_json"] == new_flow

    client.delete(f"{API}/games/{gid}")


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
