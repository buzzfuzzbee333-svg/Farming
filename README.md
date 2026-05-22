# Farming

Idle game automation starter kit for:

- Config layer (JSON per game)
- Execution layer (Termux + ADB script)
- Tracking layer (Supabase schema)

## Included files

- `/supabase/idle_schema.sql` – tables for games, sessions, milestones
- `/configs/idle-bank-tycoon.json` – example game config
- `/scripts/idle_runner.sh` – generic runner that reads a config and automates taps/upgrades

## Usage

```bash
bash /data/data/com.termux/files/home/idle_runner.sh /sdcard/idle_configs/idle-bank-tycoon.json 45
```
