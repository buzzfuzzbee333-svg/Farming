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
    is_active: bool = True


class IdleGameUpdate(BaseModel):
    name: Optional[str] = None
    package_name: Optional[str] = None
    base_payout_cents: Optional[int] = None
    est_minutes: Optional[int] = None
    config_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class IdleGame(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    package_name: str
    platform: str = "android"
    base_payout_cents: int
    est_minutes: int
    config_json: Dict[str, Any]
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


@app.on_event("startup")
async def on_startup():
    # Auto-seed on first boot
    existing = await db.idle_games.count_documents({})
    if existing == 0:
        logger.info("No games found. Auto-seeding default games...")
        await seed_data(force=False)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
