import unittest
from datetime import datetime, timedelta, timezone

from scripts.live_poll_plan import poll_plan


class LivePollPlanTests(unittest.TestCase):
    def payload(self, starts: datetime, section: str = "next_game") -> dict:
        game = {"id": "test-game", "starts_at": starts.isoformat()}
        return {section: game, "all_upcoming": [], "results": []}

    def test_too_early_does_not_consume_a_runner(self):
        now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
        self.assertIsNone(poll_plan(self.payload(now + timedelta(minutes=91)), now))

    def test_ninety_minute_window_fits_runner_limit(self):
        now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
        plan = poll_plan(self.payload(now + timedelta(minutes=90)), now)
        self.assertEqual(plan["wait_seconds"], 70 * 60)
        self.assertLessEqual(plan["end_epoch"] - int(now.timestamp()), 330 * 60)

    def test_live_game_dispatches_immediately(self):
        now = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)
        plan = poll_plan(self.payload(now - timedelta(hours=1), "live_game"), now)
        self.assertEqual(plan["wait_seconds"], 0)

    def test_recent_final_remains_in_postgame_window(self):
        now = datetime(2026, 11, 15, 19, 0, tzinfo=timezone.utc)
        game = {"id": "final", "starts_at": (now - timedelta(hours=3)).isoformat()}
        plan = poll_plan({"results": [game], "all_upcoming": []}, now)
        self.assertEqual(plan["game_id"], "final")

    def test_old_result_stops_polling(self):
        now = datetime(2026, 11, 15, 21, 0, tzinfo=timezone.utc)
        game = {"id": "old", "starts_at": (now - timedelta(hours=4, seconds=1)).isoformat()}
        self.assertIsNone(poll_plan({"results": [game], "all_upcoming": []}, now))


if __name__ == "__main__":
    unittest.main()
