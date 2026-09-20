"""Cheap schedule-only check used before making official-site requests."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


payload = json.loads((Path(__file__).resolve().parents[1] / "data" / "app-data.json").read_text(encoding="utf-8"))
now = datetime.now(timezone.utc)
candidates = [payload.get("live_game"), payload.get("next_game"), *(payload.get("all_upcoming") or [])]
active = False
for game in candidates:
    if not game or not game.get("starts_at"):
        continue
    starts = datetime.fromisoformat(game["starts_at"]).astimezone(timezone.utc)
    if starts - timedelta(minutes=20) <= now <= starts + timedelta(hours=5):
        active = True
        break
print(f"active={str(active).lower()}")
