from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")


# ===== Models =====
class TapPoint(BaseModel):
    x: int
    y: int


class GameConfig(BaseModel):
    name: str
    package_name: str
    tap_regions: Dict[str, TapPoint]
    loop: Dict[str, int]
    safety: Dict[str, int]


class IdleGameCreate(BaseModel):
    name: str
    package_name: str
    base_payout_cents: int = 0
    est_minutes: int = 30
    config_json: Dict[str, Any]
    automate_flow_json: Optional[Dict[str, Any]] = None
    is_active: bool = True


class IdleGameUpdate(BaseModel):
    name: Optional[str] = None
    package_name: Optional[str] = None
    base_payout_cents: Optional[int] = None
    est_minutes: Optional[int] = None
    config_json: Optional[Dict[str, Any]] = None
    automate_flow_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class IdleGame(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    package_name: str
    platform: str = "android"
    base_payout_cents: int
    est_minutes: int
    config_json: Dict[str, Any]
    automate_flow_json: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IdleSessionCreate(BaseModel):
    game_id: str
    session_minutes: int = 30
    notes: Optional[str] = None


class IdleSessionUpdate(BaseModel):
    status: Optional[str] = None
    earned_cents: Optional[int] = None
    notes: Optional[str] = None
    ended_at: Optional[datetime] = None


class IdleSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    game_id: str
    game_name: Optional[str] = None
    session_minutes: int = 30
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    status: str = "running"
    notes: Optional[str] = None
    earned_cents: int = 0


class IdleMilestoneCreate(BaseModel):
    game_id: str
    label: str
    target_desc: str
    est_minutes: int = 30
    payout_cents: int = 0
    order_index: int = 0


class IdleMilestoneUpdate(BaseModel):
    label: Optional[str] = None
    target_desc: Optional[str] = None
    est_minutes: Optional[int] = None
    payout_cents: Optional[int] = None
    order_index: Optional[int] = None
    completed: Optional[bool] = None


class IdleMilestone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    game_id: str
    label: str
    target_desc: str
    est_minutes: int
    payout_cents: int
    order_index: int
    completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DashboardStats(BaseModel):
    total_earnings_cents: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int
    total_runtime_minutes: int
    total_games: int
    recent_sessions: List[IdleSession]


# ===== Helpers =====
def _clean(doc: dict) -> dict:
    if doc is None:
        return doc
    doc.pop("_id", None)
    return doc


# ===== Routes =====
@api_router.get("/")
async def root():
    return {"message": "Idle Game Automation API", "status": "ok"}


# --- Games ---
@api_router.post("/games", response_model=IdleGame)
async def create_game(payload: IdleGameCreate):
    game = IdleGame(**payload.dict())
    await db.idle_games.insert_one(game.dict())
    return game


@api_router.get("/games", response_model=List[IdleGame])
async def list_games(active_only: bool = False):
    query = {"is_active": True} if active_only else {}
    docs = await db.idle_games.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [IdleGame(**d) for d in docs]


@api_router.get("/games/{game_id}", response_model=IdleGame)
async def get_game(game_id: str):
    doc = await db.idle_games.find_one({"id": game_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Game not found")
    return IdleGame(**doc)


@api_router.patch("/games/{game_id}", response_model=IdleGame)
async def update_game(game_id: str, payload: IdleGameUpdate):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = await db.idle_games.update_one({"id": game_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(404, "Game not found")
    doc = await db.idle_games.find_one({"id": game_id}, {"_id": 0})
    return IdleGame(**doc)


@api_router.delete("/games/{game_id}")
async def delete_game(game_id: str):
    result = await db.idle_games.delete_one({"id": game_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Game not found")
    # cascade
    await db.idle_milestones.delete_many({"game_id": game_id})
    await db.idle_sessions.delete_many({"game_id": game_id})
    return {"deleted": True}


# --- Sessions ---
@api_router.post("/sessions", response_model=IdleSession)
async def create_session(payload: IdleSessionCreate):
    game = await db.idle_games.find_one({"id": payload.game_id}, {"_id": 0})
    if not game:
        raise HTTPException(404, "Game not found")
    session = IdleSession(
        game_id=payload.game_id,
        game_name=game["name"],
        session_minutes=payload.session_minutes,
        notes=payload.notes,
    )
    await db.idle_sessions.insert_one(session.dict())
    return session


@api_router.get("/sessions", response_model=List[IdleSession])
async def list_sessions(game_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    query: dict = {}
    if game_id:
        query["game_id"] = game_id
    if status:
        query["status"] = status
    docs = await db.idle_sessions.find(query, {"_id": 0}).sort("started_at", -1).to_list(limit)
    return [IdleSession(**d) for d in docs]


@api_router.get("/sessions/{session_id}", response_model=IdleSession)
async def get_session(session_id: str):
    doc = await db.idle_sessions.find_one({"id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Session not found")
    return IdleSession(**doc)


@api_router.patch("/sessions/{session_id}", response_model=IdleSession)
async def update_session(session_id: str, payload: IdleSessionUpdate):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    # If status moves to terminal and ended_at not set, set it
    if updates.get("status") in {"completed", "failed", "aborted"} and "ended_at" not in updates:
        updates["ended_at"] = datetime.now(timezone.utc)
    result = await db.idle_sessions.update_one({"id": session_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(404, "Session not found")
    doc = await db.idle_sessions.find_one({"id": session_id}, {"_id": 0})
    return IdleSession(**doc)


@api_router.post("/sessions/{session_id}/stop", response_model=IdleSession)
async def stop_session(session_id: str):
    doc = await db.idle_sessions.find_one({"id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Session not found")
    await db.idle_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "aborted", "ended_at": datetime.now(timezone.utc)}},
    )
    doc = await db.idle_sessions.find_one({"id": session_id}, {"_id": 0})
    return IdleSession(**doc)


@api_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    result = await db.idle_sessions.delete_one({"id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Session not found")
    return {"deleted": True}


# --- Milestones ---
@api_router.post("/milestones", response_model=IdleMilestone)
async def create_milestone(payload: IdleMilestoneCreate):
    game = await db.idle_games.find_one({"id": payload.game_id}, {"_id": 0})
    if not game:
        raise HTTPException(404, "Game not found")
    ms = IdleMilestone(**payload.dict())
    await db.idle_milestones.insert_one(ms.dict())
    return ms


@api_router.get("/milestones", response_model=List[IdleMilestone])
async def list_milestones(game_id: Optional[str] = None):
    query = {"game_id": game_id} if game_id else {}
    docs = await db.idle_milestones.find(query, {"_id": 0}).sort("order_index", 1).to_list(1000)
    return [IdleMilestone(**d) for d in docs]


@api_router.patch("/milestones/{milestone_id}", response_model=IdleMilestone)
async def update_milestone(milestone_id: str, payload: IdleMilestoneUpdate):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = await db.idle_milestones.update_one({"id": milestone_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(404, "Milestone not found")
    doc = await db.idle_milestones.find_one({"id": milestone_id}, {"_id": 0})
    return IdleMilestone(**doc)


@api_router.delete("/milestones/{milestone_id}")
async def delete_milestone(milestone_id: str):
    result = await db.idle_milestones.delete_one({"id": milestone_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Milestone not found")
    return {"deleted": True}


# --- Dashboard ---
@api_router.get("/dashboard", response_model=DashboardStats)
async def dashboard():
    games_total = await db.idle_games.count_documents({})
    active = await db.idle_sessions.count_documents({"status": "running"})
    completed = await db.idle_sessions.count_documents({"status": "completed"})
    failed = await db.idle_sessions.count_documents({"status": "failed"})

    # Earnings
    pipeline_earn = [{"$group": {"_id": None, "total": {"$sum": "$earned_cents"}}}]
    earn = await db.idle_sessions.aggregate(pipeline_earn).to_list(1)
    total_earnings = earn[0]["total"] if earn else 0

    # Runtime (sum of session_minutes for completed)
    pipeline_run = [
        {"$match": {"status": {"$in": ["completed", "failed", "aborted"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$session_minutes"}}},
    ]
    rt = await db.idle_sessions.aggregate(pipeline_run).to_list(1)
    total_runtime = rt[0]["total"] if rt else 0

    recent = await db.idle_sessions.find({}, {"_id": 0}).sort("started_at", -1).to_list(10)
    return DashboardStats(
        total_earnings_cents=int(total_earnings or 0),
        active_sessions=active,
        completed_sessions=completed,
        failed_sessions=failed,
        total_runtime_minutes=int(total_runtime or 0),
        total_games=games_total,
        recent_sessions=[IdleSession(**d) for d in recent],
    )


# --- Seed ---
@api_router.post("/seed")
async def seed_data(force: bool = False):
    existing = await db.idle_games.count_documents({})
    if existing > 0 and not force:
        return {"seeded": False, "reason": "data already exists", "games": existing}

    if force:
        await db.idle_games.delete_many({})
        await db.idle_sessions.delete_many({})
        await db.idle_milestones.delete_many({})

    games_seed = [
        {
            "name": "Idle Bank Tycoon",
            "package_name": "com.idlebank.tycoon",
            "base_payout_cents": 400,
            "est_minutes": 45,
            "config_json": {
                "name": "Idle Bank Tycoon",
                "package_name": "com.idlebank.tycoon",
                "tap_regions": {
                    "collect": {"x": 540, "y": 1600},
                    "upgrade_1": {"x": 150, "y": 1800},
                    "upgrade_2": {"x": 540, "y": 1800},
                    "upgrade_3": {"x": 930, "y": 1800},
                },
                "loop": {
                    "collect_interval_ms": 1500,
                    "upgrade_interval_ms": 8000,
                    "session_minutes": 45,
                },
                "safety": {
                    "restart_every_minutes": 15,
                    "max_runtime_minutes": 60,
                },
            },
        },
        {
            "name": "Crypto Miner Tycoon",
            "package_name": "com.cryptominer.tycoon",
            "base_payout_cents": 500,
            "est_minutes": 60,
            "config_json": {
                "name": "Crypto Miner Tycoon",
                "package_name": "com.cryptominer.tycoon",
                "tap_regions": {
                    "collect": {"x": 540, "y": 1650},
                    "upgrade_1": {"x": 150, "y": 1800},
                    "upgrade_2": {"x": 540, "y": 1800},
                    "upgrade_3": {"x": 930, "y": 1800},
                },
                "loop": {
                    "collect_interval_ms": 1500,
                    "upgrade_interval_ms": 9000,
                    "session_minutes": 60,
                },
                "safety": {
                    "restart_every_minutes": 20,
                    "max_runtime_minutes": 75,
                },
            },
        },
    ]

    created_games = []
    for g in games_seed:
        game = IdleGame(**g)
        await db.idle_games.insert_one(game.dict())
        created_games.append(game)

    # Milestones for first game
    ms_seed = [
        ("Reach Branch 5", "Upgrade bank to branch level 5", 15, 100, 1),
        ("Hire 10 Tellers", "Complete teller hiring milestone", 30, 200, 2),
        ("Daily VIP Goal", "Hit daily VIP threshold for offerwall", 45, 400, 3),
    ]
    for label, desc, em, payout, idx in ms_seed:
        ms = IdleMilestone(
            game_id=created_games[0].id,
            label=label,
            target_desc=desc,
            est_minutes=em,
            payout_cents=payout,
            order_index=idx,
        )
        await db.idle_milestones.insert_one(ms.dict())

    ms_seed2 = [
        ("Mine 1,000 Coins", "Accumulate 1,000 coins from autoclickers", 20, 150, 1),
        ("Upgrade Rig x10", "Upgrade primary rig 10 times", 40, 250, 2),
        ("Reach Tier 3", "Unlock crypto tier 3 mining", 60, 500, 3),
    ]
    for label, desc, em, payout, idx in ms_seed2:
        ms = IdleMilestone(
            game_id=created_games[1].id,
            label=label,
            target_desc=desc,
            est_minutes=em,
            payout_cents=payout,
            order_index=idx,
        )
        await db.idle_milestones.insert_one(ms.dict())

    return {"seeded": True, "games": len(created_games)}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


CRYPTO_MINER_FLOW = {
    "name": "Crypto Miner Tycoon Automation",
    "description": "Automated gameplay for Crypto Miner Tycoon using ADB tap loops, upgrade cycles, and timed session control.",
    "version": 1,
    "nodes": [
        {"id": 1, "type": "variables_set", "name": "Load Config", "variables": {"pkg": "com.cryptominer.tycoon", "collect_x": 540, "collect_y": 1650, "up1_x": 150, "up1_y": 1800, "up2_x": 540, "up2_y": 1800, "up3_x": 930, "up3_y": 1800, "collect_ms": 1500, "upgrade_ms": 9000, "restart_minutes": 20, "session_minutes": 60}},
        {"id": 2, "type": "shell_command", "name": "Launch Game", "command": "adb shell monkey -p ${pkg} -c android.intent.category.LAUNCHER 1", "wait": True},
        {"id": 3, "type": "delay", "name": "Wait for Game Load", "delay_ms": 15000},
        {"id": 4, "type": "loop", "name": "Main Automation Loop", "iterations": -1},
        {"id": 5, "type": "shell_command", "name": "Tap Collect", "command": "adb shell input tap ${collect_x} ${collect_y}", "wait": False},
        {"id": 6, "type": "delay", "name": "Collect Delay", "delay_ms": "${collect_ms}"},
        {"id": 7, "type": "expression", "name": "Check Upgrade Timer", "expression": "now() - flow.last_upgrade >= ${upgrade_ms}"},
        {"id": 8, "type": "shell_command", "name": "Tap Upgrade 1", "command": "adb shell input tap ${up1_x} ${up1_y}", "wait": False},
        {"id": 9, "type": "shell_command", "name": "Tap Upgrade 2", "command": "adb shell input tap ${up2_x} ${up2_y}", "wait": False},
        {"id": 10, "type": "shell_command", "name": "Tap Upgrade 3", "command": "adb shell input tap ${up3_x} ${up3_y}", "wait": False},
        {"id": 11, "type": "variables_set", "name": "Reset Upgrade Timer", "variables": {"last_upgrade": "now()"}},
        {"id": 12, "type": "expression", "name": "Check Restart Timer", "expression": "now() - flow.last_restart >= (${restart_minutes} * 60000)"},
        {"id": 13, "type": "shell_command", "name": "Force Stop Game", "command": "adb shell am force-stop ${pkg}", "wait": True},
        {"id": 14, "type": "shell_command", "name": "Relaunch Game", "command": "adb shell monkey -p ${pkg} -c android.intent.category.LAUNCHER 1", "wait": True},
        {"id": 15, "type": "variables_set", "name": "Reset Restart Timer", "variables": {"last_restart": "now()"}},
        {"id": 16, "type": "expression", "name": "Check Session End", "expression": "now() - flow.start_time >= (${session_minutes} * 60000)"},
        {"id": 17, "type": "flow_end", "name": "End Session"},
        {"id": 18, "type": "variables_set", "name": "Init Timers", "variables": {"start_time": "now()", "last_upgrade": "now()", "last_restart": "now()"}},
    ],
    "connections": [
        {"from": 1, "to": 2}, {"from": 2, "to": 3}, {"from": 3, "to": 18}, {"from": 18, "to": 4},
        {"from": 4, "to": 5}, {"from": 5, "to": 6}, {"from": 6, "to": 7},
        {"from": 7, "to_true": 8, "to_false": 12},
        {"from": 8, "to": 9}, {"from": 9, "to": 10}, {"from": 10, "to": 11}, {"from": 11, "to": 12},
        {"from": 12, "to_true": 13, "to_false": 16},
        {"from": 13, "to": 14}, {"from": 14, "to": 15}, {"from": 15, "to": 16},
        {"from": 16, "to_true": 17, "to_false": 4},
    ],
}


def _flow_for_game(pkg: str, name: str) -> Dict[str, Any]:
    """Generate an Automate-style flow for any game, swapping package + coords."""
    import copy
    flow = copy.deepcopy(CRYPTO_MINER_FLOW)
    flow["name"] = f"{name} Automation"
    flow["description"] = f"Automated gameplay for {name} using ADB tap loops, upgrade cycles, and timed session control."
    flow["nodes"][0]["variables"]["pkg"] = pkg
    return flow


@app.on_event("startup")
async def on_startup():
    # Auto-seed on first boot
    existing = await db.idle_games.count_documents({})
    if existing == 0:
        logger.info("No games found. Auto-seeding default games...")
        await seed_data(force=False)

    # Backfill automate_flow_json for any existing game that lacks one
    async for g in db.idle_games.find({"automate_flow_json": {"$in": [None, {}]}}, {"_id": 0}):
        if g["package_name"] == "com.cryptominer.tycoon":
            flow = CRYPTO_MINER_FLOW
        else:
            flow = _flow_for_game(g["package_name"], g["name"])
            # tweak with the game's actual tap regions if available
            taps = g.get("config_json", {}).get("tap_regions", {})
            loop_cfg = g.get("config_json", {}).get("loop", {})
            safety = g.get("config_json", {}).get("safety", {})
            v = flow["nodes"][0]["variables"]
            if "collect" in taps:
                v["collect_x"], v["collect_y"] = taps["collect"]["x"], taps["collect"]["y"]
            if "upgrade_1" in taps:
                v["up1_x"], v["up1_y"] = taps["upgrade_1"]["x"], taps["upgrade_1"]["y"]
            if "upgrade_2" in taps:
                v["up2_x"], v["up2_y"] = taps["upgrade_2"]["x"], taps["upgrade_2"]["y"]
            if "upgrade_3" in taps:
                v["up3_x"], v["up3_y"] = taps["upgrade_3"]["x"], taps["upgrade_3"]["y"]
            if "collect_interval_ms" in loop_cfg:
                v["collect_ms"] = loop_cfg["collect_interval_ms"]
            if "upgrade_interval_ms" in loop_cfg:
                v["upgrade_ms"] = loop_cfg["upgrade_interval_ms"]
            if "session_minutes" in loop_cfg:
                v["session_minutes"] = loop_cfg["session_minutes"]
            if "restart_every_minutes" in safety:
                v["restart_minutes"] = safety["restart_every_minutes"]
        await db.idle_games.update_one({"id": g["id"]}, {"$set": {"automate_flow_json": flow}})
        logger.info(f"Backfilled automate_flow_json for {g['name']}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
