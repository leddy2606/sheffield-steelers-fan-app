import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from scripts.update_data import (
    fresher_live_score,
    is_result_score,
    parse_livescore_score,
    parse_sportplus_score,
    parse_standings,
)


def standings_page(team_label: str, team_slug: str) -> str:
    return f"""
    <table><tbody><tr>
      <td><span class="mr-3">1</span><a href="/team/5-{team_slug}">{team_label}</a></td>
      <td>10</td><td>14</td><td>4</td><td>3</td><td>3</td><td>0</td><td>34</td><td>23</td><td>0.70</td>
    </tr></tbody></table>
    """


class StandingsTeamIdentityTests(unittest.TestCase):
    def parse(self, label: str, slug: str):
        with patch("scripts.update_data.fetch", return_value=standings_page(label, slug)):
            return parse_standings("/test")[0]

    def test_qualification_marker_does_not_change_team_identity(self):
        row = self.parse("x - Cardiff Devils", "cardiff-devils")
        self.assertEqual(row["team"], "Cardiff Devils")
        self.assertEqual(row["slug"], "cardiff-devils")

    def test_unknown_future_marker_is_removed(self):
        row = self.parse("QUAL - Example Bears", "example-bears")
        self.assertEqual(row["team"], "Example Bears")
        self.assertEqual(row["slug"], "example-bears")

    def test_marker_never_falls_back_to_steelers_crest(self):
        row = self.parse("y - Guildford Flames", "guildford-flames")
        self.assertEqual(row["team"], "Guildford Flames")
        self.assertNotEqual(row["slug"], "sheffield-steelers")


class LiveScoreFallbackTests(unittest.TestCase):
    game = {"home": "Guildford Flames", "away": "Sheffield Steelers"}

    def test_sportplus_exact_team_card_is_parsed(self):
        document = """
P3 54’
![Image 1: Guildford Flames](home.png)Guildford Flames![Image 2: Sheffield Steelers](away.png)Sheffield Steelers

3  5
"""
        self.assertEqual(parse_sportplus_score(document, self.game), (3, 5))

    def test_sportplus_reversed_fixture_is_rejected(self):
        document = """![Image 1: Sheffield Steelers](a)Sheffield Steelers![Image 2: Guildford Flames](b)Guildford Flames

5 3"""
        self.assertIsNone(parse_sportplus_score(document, self.game))

    def test_livescore_requires_exact_teams(self):
        payload = {"Stages": [{"Events": [{
            "T1": [{"Nm": "Guildford Flames"}], "T2": [{"Nm": "Sheffield Steelers"}],
            "Tr1": "3", "Tr2": "5",
        }]}]}
        self.assertEqual(parse_livescore_score(payload, self.game), (3, 5))

    def test_live_score_never_rolls_back(self):
        self.assertTrue(fresher_live_score((2, 5), (3, 5)))
        self.assertFalse(fresher_live_score((3, 5), (2, 5)))
        self.assertFalse(fresher_live_score((3, 5), (3, 4)))

    def test_future_zero_zero_is_not_a_completed_result(self):
        now = datetime(2026, 11, 14, 21, 0, tzinfo=timezone.utc)
        self.assertFalse(is_result_score("0–0", now + timedelta(days=30), now))
        self.assertTrue(is_result_score("3–6", now - timedelta(minutes=1), now))


if __name__ == "__main__":
    unittest.main()
