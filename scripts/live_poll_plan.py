"""Plan one persistent free match-window poller from the published fixture data."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


payload = json.loads((Path(__file__).resolve().parents[1] / "data" / "app-data.json").read_text(encoding="utf-8"))
now = datetime.now(timezone.utc)
candidates = [
    payload.get("live_game"),
    payload.get("next_game"),
    *(payload.get("all_upcoming") or []),
    *(payload.get("results") or [])[:1],
]
game = None
for candidate in candidates:
    if not candidate or not candidate.get("starts_at"):
        continue
    starts = datetime.fromisoformat(candidate["starts_at"]).astimezone(timezone.utc)
    if starts - timedelta(hours=4) <= now <= starts + timedelta(hours=5):
        game = candidate
        break

if not game:
    print("ready=false")
else:
    starts = datetime.fromisoformat(game["starts_at"]).astimezone(timezone.utc)
    wait_seconds = max(0, int((starts - timedelta(minutes=20) - now).total_seconds()))
    end_epoch = int((starts + timedelta(hours=4)).timestamp())
    print("ready=true")
    print(f"game_id={game.get('id', 'steelers-game')}")
    print(f"wait_seconds={wait_seconds}")
    print(f"end_epoch={end_epoch}")
