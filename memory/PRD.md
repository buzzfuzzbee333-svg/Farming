# Idle Game Automation — Control App (Expo)

## Purpose
Mobile companion control app for a Termux + ADB + Supabase + Automate + n8n idle-game farming stack. Acts as the dashboard, config manager, and session log for an automation pipeline running idle games (Idle Bank Tycoon, Crypto Miner Tycoon, etc.).

## Stack
- **Frontend**: Expo Router (React Native), terminal/CLI dark aesthetic
- **Backend**: FastAPI + Motor (async MongoDB)
- **DB**: MongoDB (mirrors the Supabase schema in spec — games / sessions / milestones)
- **Auth**: none (single-user)

## Data Model
- `idle_games`: id, name, package_name, platform, base_payout_cents, est_minutes, config_json (tap_regions, loop, safety), is_active
- `idle_sessions`: id, game_id, game_name (denormalized), session_minutes, started_at, ended_at, status (running|completed|failed|aborted), notes, earned_cents
- `idle_milestones`: id, game_id, label, target_desc, est_minutes, payout_cents, order_index, completed

## Features
- **Dashboard**: TOTAL_EARNINGS hero card, Active/Runtime/Games stats, recent sessions feed, quick-start CTA
- **Games**: list, add (with raw JSON config editor), detail (config viewer, milestones, activate/pause toggle, delete with cascade)
- **Sessions**: filterable history (all/running/completed/failed/aborted), in-session COMPLETE/ABORT actions
- **Milestones**: per-game checklist with payout + ETA, tap to toggle complete
- **Start Session**: pick game + preset minutes (15/30/45/60/90) + optional notes
- Auto-seeds Idle Bank Tycoon and Crypto Miner Tycoon with default tap-coords on first boot

## Backend Endpoints (/api)
GET `/dashboard` · CRUD `/games` `/sessions` `/milestones` · POST `/sessions/{id}/stop` · POST `/seed`

## Out of Scope (for now)
- ADB execution from app (handled by the Termux+Automate layer outside)
- Discord/Notion webhook bolt-on
- Multi-user / auth
- Push notifications

## Smart Enhancement Hook
**Payout-per-minute leaderboard**: Sort games by `base_payout_cents / est_minutes` so the n8n rotation flow can pick the best ROI run automatically. Already wired in data model — surface in UI next iteration.
