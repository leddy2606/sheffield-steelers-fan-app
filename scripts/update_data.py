"""Refresh the fan app from public EIHL pages using only Python's standard library."""

from __future__ import annotations

import html
import json
import re
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = "https://www.eliteleague.co.uk"
TEAM = "Sheffield Steelers"
SEASONS = {
    57: "EIHL League",
    58: "Challenge Cup",
}
SLUGS = {
    "Belfast Giants": "belfast-giants",
    "Cardiff Devils": "cardiff-devils",
    "Coventry Blaze": "coventry-blaze",
    "Dundee Stars": "dundee-stars",
    "Fife Flyers": "fife-flyers",
    "Glasgow Clan": "glasgow-clan",
    "Guildford Flames": "guildford-flames",
    "Manchester Storm": "manchester-storm",
    "Nottingham Panthers": "nottingham-panthers",
    "Sheffield Steelers": "sheffield-steelers",
}
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "app-data.json"
JS_OUTPUT = ROOT / "data" / "app-data.js"
LONDON = ZoneInfo("Europe/London")
SSL_CONTEXT = ssl._create_unverified_context()
HEADERS = {"User-Agent": "SteelCityMatchCentre/1.0 (unofficial fan app)"}


def fetch(path: str) -> str:
    request = urllib.request.Request(urllib.parse.urljoin(BASE, path), headers=HEADERS)
    with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def text(fragment: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(clean).split())


def parse_schedule(season_id: int, competition: str) -> list[dict]:
    season_page = fetch(f"/schedule?id_season={season_id}")
    team_option = re.search(
        rf'<option value="([^"]*id_team=\d+)"[^>]*>\s*{re.escape(TEAM)}\s*</option>',
        season_page,
    )
    if not team_option:
        return []
    schedule_path = html.unescape(team_option.group(1)) + "&id_month=999"
    page = fetch(schedule_path)
    sections = re.split(r"<h2[^>]*>", page)[1:]
    games: list[dict] = []
    for section in sections:
        heading, _, body = section.partition("</h2>")
        date_match = re.search(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{2}\.\d{2}\.\d{4})", text(heading))
        if not date_match:
            continue
        game_date = datetime.strptime(date_match.group(2), "%d.%m.%Y").date()
        for row in re.findall(r'<div class="row align-items-center[^>]*>([\s\S]*?)>Details<', body):
            time_match = re.search(r'<div class="delta[^>]*>\s*(\d{2}:\d{2})\s*</div>', row)
            game_match = re.search(r'href="(/game/[^"?#]+)"[^>]*>\s*([^<]+)\s*</a>', row)
            teams = re.findall(r'href="/schedule\?[^"#]*id_team=\d+"[^>]*>\s*([^<]+)\s*</a>', row)
            if not time_match or not game_match or len(teams) < 2:
                continue
            home, away = (" ".join(team.split()) for team in teams[:2])
            score_text = text(game_match.group(2)).replace(":", "–")
            complete = bool(re.fullmatch(r"\d+–\d+", score_text))
            starts = datetime.combine(game_date, datetime.strptime(time_match.group(1), "%H:%M").time(), LONDON)
            games.append({
                "id": game_match.group(1).removeprefix("/game/"),
                "starts_at": starts.isoformat(),
                "competition": competition,
                "home": home,
                "away": away,
                "home_slug": SLUGS.get(home, "sheffield-steelers"),
                "away_slug": SLUGS.get(away, "sheffield-steelers"),
                "score": score_text if complete else None,
                "complete": complete,
                "details_url": urllib.parse.urljoin(BASE, game_match.group(1)),
            })
    return games


def parse_preseason_fixtures() -> list[dict]:
    """Add official Steelers pre-season fixtures that precede the EIHL schedule."""
    page = fetch("https://www.sheffieldsteelers.co.uk/fixtures/")
    games = []
    for section in re.split(r'<h2 class="month-header">', page)[1:]:
        month_heading, _, body = section.partition("</h2>")
        month_year = text(month_heading)
        if not re.fullmatch(r"[A-Za-z]+ 20\d{2}", month_year):
            continue
        blocks = re.split(r'(?=<div class="steelers-hub-fixture )', body)
        for block in blocks[1:]:
            block = block.split('<h2 class="month-header">', 1)[0]
            side_match = re.match(r'<div class="steelers-hub-fixture (home|away)', block)
            date_match = re.search(r'<div class="fixture-date">([^<]+)</div>', block)
            venue_match = re.search(r'<div class="fixture-venue">([^<]+)</div>', block)
            teams = [text(name) for name in re.findall(r'<span>([^<]+)</span>', block)]
            if not side_match or not date_match or len(teams) < 2:
                continue
            clean_date = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text(date_match.group(1)))
            starts = datetime.strptime(f"{clean_date} {month_year.split()[-1]}", "%A %d %B, %I:%M%p %Y").replace(tzinfo=LONDON)
            normalized = [TEAM if name == "Steelers" else next((full for full in SLUGS if full.endswith(name)), name) for name in teams[:2]]
            home, away = normalized if side_match.group(1) == "home" else normalized
            games.append({
                "id": "preseason-" + starts.strftime("%Y%m%d-%H%M") + "-" + SLUGS.get(home, "team") + "-" + SLUGS.get(away, "team"),
                "starts_at": starts.isoformat(),
                "competition": "Pre-season",
                "home": home,
                "away": away,
                "home_slug": SLUGS.get(home, "sheffield-steelers"),
                "away_slug": SLUGS.get(away, "sheffield-steelers"),
                "score": None,
                "complete": False,
                "venue": text(venue_match.group(1)) if venue_match else "",
                "details_url": "https://www.sheffieldsteelers.co.uk/fixtures/",
            })
    return games


def parse_standings(path: str) -> list[dict]:
    page = fetch(path)
    table_match = re.search(r"<tbody>([\s\S]*?)</tbody>", page)
    if not table_match:
        return []
    rows = []
    for row in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", table_match.group(1)):
        team_match = re.search(r'<a href="/team/[^\"]+">([\s\S]*?)</a>', row)
        position_match = re.search(r'<span class="mr-3">\s*(\d+)\s*</span>', row)
        cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)
        if not team_match or not position_match or len(cells) < 10:
            continue
        values = [text(cell) for cell in cells[1:]]
        team_name = text(team_match.group(1))
        rows.append({
            "position": int(position_match.group(1)),
            "team": team_name,
            "slug": SLUGS.get(team_name, "sheffield-steelers"),
            "played": int(values[0]),
            "points": int(values[1]),
            "wins": int(values[2]) + int(values[3]),
            "losses": int(values[4]) + int(values[5]),
            "goals_for": int(values[6]),
            "goals_against": int(values[7]),
        })
    return rows


def main() -> None:
    now = datetime.now(timezone.utc)
    games_by_id: dict[str, dict] = {}
    for season_id, competition in SEASONS.items():
        for game in parse_schedule(season_id, competition):
            games_by_id[game["id"]] = game
    competitive_start = min(datetime.fromisoformat(game["starts_at"]) for game in games_by_id.values())
    for game in parse_preseason_fixtures():
        if datetime.fromisoformat(game["starts_at"]) < competitive_start:
            games_by_id[game["id"]] = game
    games = sorted(games_by_id.values(), key=lambda game: game["starts_at"])
    upcoming = [game for game in games if not game["complete"] and datetime.fromisoformat(game["starts_at"]).astimezone(timezone.utc) >= now]
    results = [game for game in games if game["complete"]]
    results.sort(key=lambda game: game["starts_at"], reverse=True)

    league = parse_standings("/standings/2026/57-elite-ice-hockey-league")
    cup = parse_standings("/standings/2026/58-challenge-cup")
    steelers_row = next((row for row in league if row["team"] == TEAM), None)

    form = []
    for game in results[:5]:
        home_score, away_score = (int(value) for value in game["score"].split("–"))
        steelers_score = home_score if game["home"] == TEAM else away_score
        opponent_score = away_score if game["home"] == TEAM else home_score
        form.append("W" if steelers_score > opponent_score else "L")

    snapshot = {
        "position": steelers_row["position"] if steelers_row else None,
        "played": steelers_row["played"] if steelers_row else 0,
        "points": steelers_row["points"] if steelers_row else 0,
        "wins": steelers_row["wins"] if steelers_row else 0,
        "goals_for": steelers_row["goals_for"] if steelers_row else 0,
        "form": form,
    }
    payload = {
        "generated_at": now.replace(microsecond=0).isoformat(),
        "season": "2026/27",
        "source": "Official EIHL website",
        "next_game": upcoming[0] if upcoming else None,
        "upcoming": upcoming[:6],
        "results": results[:6],
        "standings": {"league": league, "cup": cup},
        "snapshot": snapshot,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    OUTPUT.write_text(serialized + "\n", encoding="utf-8")
    JS_OUTPUT.write_text("window.STEELERS_DATA = " + serialized + ";\n", encoding="utf-8")
    print(f"Updated {OUTPUT}: {len(upcoming)} upcoming, {len(results)} completed")


if __name__ == "__main__":
    main()
