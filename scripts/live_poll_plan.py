"""Plan one persistent free match-window poller from published fixture data."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def poll_plan(payload: dict, now: datetime) -> dict | None:
    """Return a bounded poll plan for the closest current fixture, if any."""
    checked_at = now.astimezone(timezone.utc)
    candidates = [
        payload.get("live_game"),
        payload.get("next_game"),
        *(payload.get("all_upcoming") or []),
        *(payload.get("results") or [])[:1],
    ]
    for game in candidates:
        if not game or not game.get("starts_at"):
            continue
        starts = datetime.fromisoformat(game["starts_at"]).astimezone(timezone.utc)
        # Ninety minutes before face-off plus four hours after it fits safely
        # within GitHub's six-hour hosted-job limit, including setup overhead.
        if starts - timedelta(minutes=90) <= checked_at <= starts + timedelta(hours=4):
            return {
                "game_id": game.get("id", "steelers-game"),
                "wait_seconds": max(0, int((starts - timedelta(minutes=20) - checked_at).total_seconds())),
                "end_epoch": int((starts + timedelta(hours=4)).timestamp()),
            }
    return None


def main() -> None:
    payload = json.loads((Path(__file__).resolve().parents[1] / "data" / "app-data.json").read_text(encoding="utf-8"))
    plan = poll_plan(payload, datetime.now(timezone.utc))
    if not plan:
        print("ready=false")
        return
    print("ready=true")
    for key, value in plan.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
