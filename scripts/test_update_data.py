import unittest
from unittest.mock import patch

from scripts.update_data import parse_standings


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


if __name__ == "__main__":
    unittest.main()
