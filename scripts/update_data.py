"""Refresh the fan app from official EIHL and Sheffield Steelers sources."""

from __future__ import annotations

import html
import io
import json
import re
import ssl
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
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
LIVE_DATA_URL = "https://leddy2606.github.io/sheffield-steelers-fan-app/data/app-data.json"
LONDON = ZoneInfo("Europe/London")
SSL_CONTEXT = ssl._create_unverified_context()
HEADERS = {"User-Agent": "SteelCityMatchCentre/1.0 (unofficial fan app)"}
ROSTER_TRACKER = "/article/5422-2026-27-rosters"
ROSTER_PAGE = "/team/13-sheffield-steelers/roster?id_season=57"
MONTHS = {name.lower(): number for number, name in enumerate((
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)) if name}
CONFIRMED_NUMBERS = {
    "Lucas Brine": "44", "Matt Greenfield": "1", "Aatu Aarnio": "77",
    "Dominic Cormier": "58", "Brien Diffley": "65", "Macoy Erkamps": "59",
    "Logan Roe": "57", "Liam Steele": "3", "Olivier Archambault": "93",
    "Mitchell Balmas": "92", "Ivan Björkly Nordström": "72", "Robert Dowd": "75",
    "Evan Jasper": "62", "Mikko Juusola": "63", "Ryan Tait": "8",
    "Leevi Teissala": "71", "Brandon Whistle": "74",
}
GAMESHEET_NAME_CORRECTIONS = {"Leevi Tiessala": "Leevi Teissala"}
OFFICIAL_VIDEO_FEEDS = (
    ("Sheffield Steelers TV", "https://www.youtube.com/feeds/videos.xml?channel_id=UCkROPc1dZwX75lukXesiAsg"),
)
TICKET_PAGES = {
    "Belfast Giants": "https://www.belfastgiants.com/game-centre",
    "Cardiff Devils": "https://www.cardiffdevils.com/tickets/match-night-tickets/",
    "Coventry Blaze": "https://coventryblaze.co.uk/tickets/",
    "Dundee Stars": "https://www.dundeestars.com/matches/",
    "Fife Flyers": "https://fifeflyers.co.uk/tickets-2/",
    "Glasgow Clan": "https://clanihc.com/tickets/game-day-tickets/",
    "Guildford Flames": "https://www.guildfordflames.co.uk/tickets",
    "Manchester Storm": "https://www.ticketmaster.co.uk/manchester-storm-tickets/artist/5223012",
    "Nottingham Panthers": "https://www.panthers.co.uk/tickets",
    "Sheffield Steelers": "https://www.ticketmaster.co.uk/sheffield-steelers-tickets/artist/30123?brand=uk_sheffieldarena&venueId=435513",
}


def fetch_bytes(path: str) -> bytes:
    request = urllib.request.Request(urllib.parse.urljoin(BASE, path), headers=HEADERS)
    with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=30) as response:
        return response.read()


def fetch(path: str) -> str:
    return fetch_bytes(path).decode("utf-8", "ignore")


def text(fragment: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(clean).split())


def ordinal_day(day: int) -> str:
    suffix = "th" if 10 < day % 100 < 14 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def parse_video_feed(source: str, feed_url: str) -> list[dict]:
    """Read an official YouTube Atom feed without requiring an API key."""
    root = ET.fromstring(fetch_bytes(feed_url))
    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    videos = []
    for entry in root.findall("atom:entry", namespaces):
        video_id = entry.findtext("yt:videoId", default="", namespaces=namespaces)
        title = entry.findtext("atom:title", default="", namespaces=namespaces)
        published = entry.findtext("atom:published", default="", namespaces=namespaces)
        description = entry.findtext("media:group/media:description", default="", namespaces=namespaces)
        thumbnail = entry.find("media:group/media:thumbnail", namespaces)
        if not video_id or not title or not published:
            continue
        videos.append({
            "video_id": video_id,
            "title": title,
            "description": description,
            "published_at": published,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}",
            "thumbnail_url": thumbnail.get("url") if thumbnail is not None else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "source": source,
        })
    return videos


def match_highlight_video(game: dict, videos: list[dict]) -> dict | None:
    """Match an official highlight upload to a completed fixture conservatively."""
    game_day = datetime.fromisoformat(game["starts_at"]).date()
    opponent = game["away"] if game["home"] == TEAM else game["home"]
    opponent_alias = opponent.split()[-1].lower()
    date_markers = {
        game_day.strftime("%Y-%m-%d"),
        game_day.strftime("%d/%m/%Y"),
        f"{game_day.day} {game_day.strftime('%B %Y')}".lower(),
        f"{ordinal_day(game_day.day)} {game_day.strftime('%B %Y')}".lower(),
    }
    candidates = []
    for video in videos:
        published_day = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00")).date()
        days_after_game = (published_day - game_day).days
        combined = f'{video["title"]} {video.get("description", "")}'.lower()
        if not 0 <= days_after_game <= 10 or "steelers" not in combined or opponent_alias not in combined:
            continue
        exact_date = any(marker in combined for marker in date_markers)
        looks_like_highlights = "highlight" in combined or bool(re.search(r"steelers\s+(?:v|vs)\s+", combined))
        if exact_date and looks_like_highlights:
            candidates.append((days_after_game, video))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def embedded_youtube_video(page_url: str) -> dict | None:
    """Use a YouTube video embedded in an official match report as a backup."""
    page = fetch(page_url)
    video = re.search(
        r"<iframe[^>]+src=[\"'][^\"']*(?:youtube(?:-nocookie)?\.com/embed/)([A-Za-z0-9_-]{11})",
        page,
        re.I,
    )
    if not video:
        return None
    video_id = video.group(1)
    return {
        "video_id": video_id,
        "title": "Official match highlights",
        "published_at": "",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "source": "Official match report",
    }


def add_ticket_links(games: list[dict]) -> None:
    """Attach an exact official ticket event when discoverable, otherwise the home club's ticket page."""
    ticketmaster_pages: dict[str, str] = {}
    for game in games:
        home_team = game.get("home")
        fallback = TICKET_PAGES.get(home_team)
        if not fallback:
            continue
        game["ticket_url"] = fallback
        game["ticket_exact"] = False
        if "ticketmaster.co.uk" not in fallback:
            continue
        if fallback not in ticketmaster_pages:
            try:
                ticketmaster_pages[fallback] = fetch(fallback)
            except Exception as error:
                print(f"Exact {home_team} ticket listings unavailable; using official ticket page: {error}")
                ticketmaster_pages[fallback] = ""
        page = html.unescape(ticketmaster_pages[fallback]).replace("\\/", "/")
        game_day = datetime.fromisoformat(game["starts_at"]).date()
        home_alias = home_team.split()[-1].lower()
        away_alias = game["away"].split()[-1].lower()
        for event_url in dict.fromkeys(re.findall(r"https://www\.ticketmaster\.co\.uk/[^\"'\\\s]+/event/[A-Za-z0-9]+", page)):
            slug = urllib.parse.unquote(event_url).lower()
            if "parking" in slug or game_day.strftime("%d-%m-%Y") not in slug:
                continue
            if home_alias in slug and away_alias in slug:
                game["ticket_url"] = event_url
                game["ticket_exact"] = True
                break


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
            has_score = bool(re.fullmatch(r"\d+–\d+", score_text))
            starts = datetime.combine(game_date, datetime.strptime(time_match.group(1), "%H:%M").time(), LONDON)
            games.append({
                "id": game_match.group(1).removeprefix("/game/"),
                "starts_at": starts.isoformat(),
                "competition": competition,
                "home": home,
                "away": away,
                "home_slug": SLUGS.get(home, "sheffield-steelers"),
                "away_slug": SLUGS.get(away, "sheffield-steelers"),
                "score": score_text if has_score else None,
                "complete": has_score,
                "live": False,
                "status": "Final" if has_score else "Scheduled",
                "details_url": urllib.parse.urljoin(BASE, game_match.group(1)),
            })
    return games


def period_for_time(goal_time: str) -> str:
    if goal_time.lower().startswith("opening"):
        return "1st period"
    match = re.match(r"(\d{1,3}):", goal_time)
    if not match:
        return "Period unavailable"
    minute = int(match.group(1))
    if minute < 20:
        return "1st period"
    if minute < 40:
        return "2nd period"
    if minute < 60:
        return "3rd period"
    return "Overtime"


def parse_goal_list(fragment: str, team: str) -> list[dict]:
    goals = []
    for item in re.findall(r"<li[^>]*>([\s\S]*?)</li>", fragment):
        scorer = re.search(r'<a href="/player/[^\"]+">([^<]+)</a>', item)
        goal_time = re.search(r'<span class="text-gray[^>]*>\s*(\d{1,3}:\d{2})\s*</span>', item)
        if scorer and goal_time:
            exact_time = text(goal_time.group(1))
            goals.append({"team": team, "scorer": text(scorer.group(1)), "time": exact_time, "period": period_for_time(exact_time)})
    return goals


def parse_eihl_game_details(game: dict) -> dict:
    """Read current status, score and Steelers scorers from an official game page."""
    page = fetch(game["details_url"])
    status_match = re.search(r'<div class="text-gray font-secondary font-size-bigger">([\s\S]*?)</div>\s*<div class="match-score', page)
    raw_status = text(status_match.group(1)) if status_match else ""
    score_match = re.search(r'<div class="match-score[^>]*>\s*(\d+)\s*:\s*(\d+)\s*</div>', page)
    score = f"{score_match.group(1)}–{score_match.group(2)}" if score_match else game.get("score")
    normalized = raw_status.lower()
    complete = normalized in {"end", "final", "finished"} or normalized.startswith(("end ", "final ", "finished "))
    scheduled = not raw_status or "before game" in normalized or "game starts" in normalized
    live = bool(raw_status and not complete and not scheduled)
    live_status = raw_status[:1].upper() + raw_status[1:] if raw_status else "Live"
    status = "Final" if complete else ("Scheduled" if scheduled else live_status)
    goal_lists = re.findall(r'<ul class="d-none d-lg-block">([\s\S]*?)</ul>', page)
    scorers = []
    for index, team in enumerate((game["home"], game["away"])):
        if len(goal_lists) > index:
            scorers.extend(parse_goal_list(goal_lists[index], team))
    details = {"score": score, "complete": complete, "live": live, "status": status, "scorers": scorers}
    if complete:
        starts = datetime.fromisoformat(game["starts_at"]).astimezone(LONDON)
        finished_at = starts + timedelta(hours=3)
        gamesheet = re.search(r'href="(https://eihlhq\.co\.uk/pdf/print/de-html/\d+)"', page)
        if gamesheet:
            try:
                sheet = fetch(gamesheet.group(1))
                end_time = re.search(r"Local end time:\s*(\d{1,2}):(\d{2})", sheet, re.I)
                if end_time:
                    finished_at = datetime.combine(
                        starts.date(),
                        datetime.strptime(f"{end_time.group(1)}:{end_time.group(2)}", "%H:%M").time(),
                        LONDON,
                    )
                    if finished_at < starts:
                        finished_at += timedelta(days=1)
            except Exception as error:
                print(f"Exact final-whistle time unavailable for {game.get('id', 'game')}: {error}")
        details["finished_at"] = finished_at.isoformat()
        details["featured_until"] = (finished_at + timedelta(hours=1)).isoformat()
    return details


def parse_preseason_fixtures(player_names: list[str]) -> list[dict]:
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
            game = {
                "id": "preseason-" + starts.strftime("%Y%m%d-%H%M") + "-" + SLUGS.get(home, "team") + "-" + SLUGS.get(away, "team"),
                "starts_at": starts.isoformat(),
                "competition": "Pre-season",
                "home": home,
                "away": away,
                "home_slug": SLUGS.get(home, "sheffield-steelers"),
                "away_slug": SLUGS.get(away, "sheffield-steelers"),
                "score": None,
                "complete": False,
                "live": False,
                "status": "Scheduled",
                "scorers": [],
                "venue": text(venue_match.group(1)) if venue_match else "",
                "details_url": "https://www.sheffieldsteelers.co.uk/fixtures/",
            }
            if starts.astimezone(timezone.utc) < datetime.now(timezone.utc) - timedelta(hours=2):
                try:
                    result = parse_preseason_result(game, player_names)
                    if result:
                        game.update(result)
                except Exception as error:
                    print(f"Pre-season result lookup unavailable for {starts.date()}: {error}")
            games.append(game)
    return games


def parse_report_scorers(report_text: str, player_names: list[str]) -> list[dict]:
    """Extract Steelers scorers, game times and periods from an official club recap."""
    final_list_at = max(report_text.lower().rfind("steelers goals:"), report_text.lower().rfind("steelers goal:"))
    scorer_list = report_text[final_list_at:final_list_at + 300] if final_list_at >= 0 else ""
    scorers = []
    for name in player_names:
        occurrences = list(re.finditer(re.escape(name), report_text[:final_list_at], re.I))
        if final_list_at < 0:
            occurrences = list(re.finditer(re.escape(name), report_text, re.I))
        elif not re.search(re.escape(name), scorer_list, re.I):
            continue
        if not occurrences:
            continue
        candidates = []
        for occurrence in occurrences:
            before = report_text[max(0, occurrence.start() - 320):occurrence.start()]
            after = report_text[occurrence.end():occurrence.end() + 140]
            named_before = re.search(r"(?:scored by|goal (?:from|by))[^.]{0,70}" + re.escape(name), before[-160:] + report_text[occurrence.start():occurrence.end()], re.I)
            named_after = re.search(
                r"^(?:\W{0,8}(?:scor(?:e|ed|ing)|converted?|equalis(?:e|ed)|levelled)|[^.]{0,70}\b(?:he|the (?:returning )?forward)\b[^.]{0,45}(?:scor(?:e|ed)|finish))",
                after,
                re.I,
            )
            if named_after:
                scoring_phrase = after[:named_after.end()]
                if any(other != name and re.search(re.escape(other), scoring_phrase, re.I) for other in player_names):
                    named_after = None
            direct_score = bool(named_before or named_after)
            if final_list_at < 0 and not direct_score:
                continue
            time_evidence = bool(re.search(r"(?<!\d)\d{1,2}[.:]\d{2}(?!\d)|opening minute|\d+(?:st|nd|rd|th) minute", before, re.I))
            candidates.append((2 if time_evidence else 0, occurrence, before))
        if not candidates:
            continue
        _, scored_at, before = max(candidates, key=lambda item: item[0])
        period_matches = list(re.finditer(r"\b(First|Second|Third) Period\b", report_text[:scored_at.start()], re.I))
        period_number = {"first": 1, "second": 2, "third": 3}.get(period_matches[-1].group(1).lower(), 0) if period_matches else 0
        remaining = list(re.finditer(r"with\s+(\d{1,2}):(\d{2})\s+remaining", before, re.I))
        time_matches = list(re.finditer(r"(?<!\d)(\d{1,2})[.:](\d{2})(?!\d)", before))
        if remaining and period_number:
            minutes_left, seconds_left = (int(value) for value in remaining[-1].groups())
            elapsed = (period_number - 1) * 20 * 60 + max(0, 20 * 60 - (minutes_left * 60 + seconds_left))
            goal_time = f"{elapsed // 60}:{elapsed % 60:02d}"
        elif time_matches:
            last_time = time_matches[-1]
            goal_time = f"{int(last_time.group(1))}:{last_time.group(2)}"
        elif re.search(r"opening minute", before, re.I):
            goal_time = "Opening minute"
        else:
            minute_match = re.search(r"(\d+)(?:st|nd|rd|th) minute", before, re.I)
            goal_time = f"{minute_match.group(1)}th minute" if minute_match else "Time unavailable"
        period = f"{period_number}{'st' if period_number == 1 else 'nd' if period_number == 2 else 'rd'} period" if period_number else period_for_time(goal_time)
        scorers.append({"team": TEAM, "scorer": name, "time": goal_time, "period": period})
    def goal_order(goal: dict) -> int:
        if goal["time"].lower().startswith("opening"):
            return 0
        match = re.match(r"(\d+)", goal["time"])
        return int(match.group(1)) if match else 999
    return sorted(scorers, key=goal_order)


def parse_preseason_result(game: dict, player_names: list[str]) -> dict | None:
    """Find a completed exhibition score in the club's official match report."""
    game_day = datetime.fromisoformat(game["starts_at"]).date()
    query = urllib.parse.urlencode({
        "after": f"{game_day.isoformat()}T00:00:00",
        "before": f"{(game_day + timedelta(days=1)).isoformat()}T00:00:00",
        "per_page": 30,
    })
    posts = json.loads(fetch(f"https://www.sheffieldsteelers.co.uk/wp-json/wp/v2/posts?{query}"))
    opponent = game["away"] if game["home"] == TEAM else game["home"]
    opponent_alias = opponent.split()[-1].lower()
    outcome_words = r"win|wins|won|victory|beat|beats|defeat|defeats|edge|edges"
    loss_words = r"lose|loses|lost|loss|beaten|go down|fall"
    for post in posts:
        title = text(post.get("title", {}).get("rendered", ""))
        excerpt = text(post.get("excerpt", {}).get("rendered", ""))
        report_text = text(post.get("content", {}).get("rendered", ""))
        document = " ".join((title, excerpt, report_text))
        final_line = re.search(r"Final Score:\s*([^.]*)", document, re.I)
        score_matches = list(re.finditer(r"(?<!\d)(\d{1,2})\s*[-–]\s*(\d{1,2})(?!\d)", final_line.group(1) if final_line else document))
        score_match = score_matches[-1] if score_matches else None
        words = set(re.findall(r"[a-z]+", document.lower()))
        if not score_match or not ({"steelers", opponent_alias} <= words):
            continue
        first, second = (int(value) for value in score_match.groups())
        if first == second:
            continue
        lower = document.lower()
        steelers_first = bool(re.search(rf"(?:sheffield\s+)?steelers\s*{first}\s*[-–]\s*{second}\s*(?:\w+\s+)?{re.escape(opponent_alias)}", document, re.I))
        opponent_first = bool(re.search(rf"{re.escape(opponent_alias)}(?:\s+\w+)?\s*{first}\s*[-–]\s*{second}\s*(?:sheffield\s+)?steelers", document, re.I))
        if steelers_first or opponent_first:
            steelers_score, opponent_score = (first, second) if steelers_first else (second, first)
            home_score, away_score = (steelers_score, opponent_score) if game["home"] == TEAM else (opponent_score, steelers_score)
            steelers_won = steelers_score > opponent_score
            opponent_won = opponent_score > steelers_score
        else:
            steelers_won = bool(re.search(rf"steelers.{{0,80}}(?:{outcome_words})", lower))
            opponent_won = bool(re.search(rf"{re.escape(opponent_alias)}.{{0,80}}(?:{outcome_words})", lower))
            if re.search(rf"steelers.{{0,80}}(?:{loss_words})", lower):
                opponent_won = True
            if re.search(rf"{re.escape(opponent_alias)}.{{0,80}}(?:{loss_words})", lower):
                steelers_won = True
            if steelers_won == opponent_won:
                continue
            high, low = max(first, second), min(first, second)
            home_won = steelers_won if game["home"] == TEAM else opponent_won
            home_score, away_score = (high, low) if home_won else (low, high)
        return {
            "score": f"{home_score}–{away_score}",
            "complete": True,
            "live": False,
            "status": "Final",
            "scorers": parse_report_scorers(report_text, player_names),
            "finished_at": (datetime.fromisoformat(game["starts_at"]) + timedelta(hours=3)).isoformat(),
            "featured_until": (datetime.fromisoformat(game["starts_at"]) + timedelta(hours=4)).isoformat(),
            "details_url": post.get("link", game["details_url"]),
        }
    return None


def parse_preseason_hub(previous_url: str = "") -> tuple[list[dict], str]:
    """Read the league-wide friendly results maintained on the official EIHL hub."""
    homepage = fetch("/")
    hub_match = re.search(
        r'href="(?:https://www\.eliteleague\.co\.uk)?(/article/\d+-pre-season-\d{4}-\d{2})"',
        homepage,
        re.I,
    )
    hub_path = hub_match.group(1) if hub_match else urllib.parse.urlparse(previous_url).path
    if not hub_path.startswith("/article/"):
        raise ValueError("Official pre-season hub link was not found")
    page = fetch(hub_path)
    article = re.search(r'<article class="pt-3 pb-3 p-lg-6 typography">([\s\S]*?)</article>', page)
    if not article:
        raise ValueError("Official pre-season hub content was not found")
    season_match = re.search(r"Pre-Season\s+(20\d{2})/\d{2}", text(article.group(1)), re.I)
    season_year = int(season_match.group(1)) if season_match else datetime.now(LONDON).year
    line_html = re.sub(r"<br\s*/?>", "\n", article.group(1), flags=re.I)
    line_html = re.sub(r"</?(?:p|li|h[1-6])[^>]*>", "\n", line_html, flags=re.I)
    lines = [text(line) for line in line_html.splitlines() if text(line)]
    current_month = None
    current_day = None
    games = []
    for line in lines:
        if line.lower() in MONTHS:
            current_month = MONTHS[line.lower()]
            continue
        date_heading = re.match(
            r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})(?:\s+(January|February|March|April|May|June|July|August|September|October|November|December))?(?:\s+(.*))?$",
            line,
            re.I,
        )
        if date_heading:
            current_day = int(date_heading.group(1))
            if date_heading.group(2) and date_heading.group(2).lower() in MONTHS:
                current_month = MONTHS[date_heading.group(2).lower()]
            line = (date_heading.group(3) or "").strip()
            if not line:
                continue
        clean_line = re.sub(r"\s*\|\s*(?:G\s*amesheet|Match Report).*$", "", line, flags=re.I).strip()
        score = re.fullmatch(
            r"(.+?)\s+(\d{1,2})\s*[-–:√]\s*(\d{1,2})(?:\s+(OT|SO))?\s+(.+)",
            clean_line,
            re.I,
        )
        if not score or not current_month or not current_day:
            continue
        home, home_score, away_score, overtime, away = score.groups()
        home, away = home.strip(), away.strip()
        if home not in SLUGS and away not in SLUGS:
            continue
        gamesheet = re.search(
            rf"{re.escape(home)}\s+{home_score}\s*[-–:]\s*{away_score}(?:\s+(?:OT|SO))?\s+"
            rf"{re.escape(away)}\s*\|\s*<a[^>]+href=\"([^\"]+)\"[^>]*>\s*<b>Gamesheet",
            article.group(1),
            re.I,
        )
        game_date = datetime(season_year, current_month, current_day, tzinfo=LONDON)
        games.append({
            "id": f"friendly-{game_date.date().isoformat()}-{SLUGS.get(home, comparable_name(home))}-{SLUGS.get(away, comparable_name(away))}",
            "date": game_date.date().isoformat(),
            "home": home,
            "away": away,
            "home_score": int(home_score),
            "away_score": int(away_score),
            "overtime": bool(overtime),
            "gamesheet_url": html.unescape(gamesheet.group(1)) if gamesheet else None,
        })
    if not games:
        raise ValueError("Official pre-season hub did not contain completed games")
    return games, urllib.parse.urljoin(BASE, hub_path)


def build_preseason_table(games: list[dict]) -> list[dict]:
    """Calculate an unofficial form table from official friendly results."""
    rows = {
        team: {
            "team": team, "slug": slug, "played": 0, "wins": 0,
            "losses": 0, "overtime_losses": 0, "points": 0,
            "goals_for": 0, "goals_against": 0,
        }
        for team, slug in SLUGS.items()
    }
    for game in games:
        for team, scored, conceded in (
            (game["home"], game["home_score"], game["away_score"]),
            (game["away"], game["away_score"], game["home_score"]),
        ):
            if team not in rows:
                continue
            row = rows[team]
            row["played"] += 1
            row["goals_for"] += scored
            row["goals_against"] += conceded
            if scored > conceded:
                row["wins"] += 1
                row["points"] += 2
            elif game.get("overtime"):
                row["overtime_losses"] += 1
                row["points"] += 1
            else:
                row["losses"] += 1
    ordered = sorted(
        rows.values(),
        key=lambda row: (-row["points"], -(row["goals_for"] - row["goals_against"]), -row["goals_for"], row["team"]),
    )
    for position, row in enumerate(ordered, 1):
        row["position"] = position
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
    return ordered


def gamesheet_player_name(raw_name: str) -> str:
    """Convert a gamesheet's SURNAME Given format into a readable player name."""
    parts = raw_name.split()
    if len(parts) < 2:
        return raw_name.title()
    return " ".join([parts[-1].title(), *(part.title() for part in parts[:-1])])


def parse_gamesheet_scorers(gamesheet_url: str, team: str = TEAM, player_names: list[str] | None = None) -> list[dict]:
    """Read scorer numbers and exact goal times from an official EIHL PDF."""
    from pypdf import PdfReader

    document = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(fetch_bytes(gamesheet_url))).pages)
    document = unicodedata.normalize("NFKD", document).encode("ascii", "ignore").decode()
    section = re.search(
        rf"(?:Home \(A\)|Visitor \(B\))\s+{re.escape(team)}\s*\n([\s\S]*?)(?=(?:Home \(A\)|Visitor \(B\))\s+|Game Summary|\Z)",
        document,
        re.I,
    )
    if not section:
        raise ValueError(f"{team} section was not found in the official gamesheet")
    team_text = section.group(1)
    roster_text, separator, remainder = team_text.partition("Goals\n")
    goals_text = remainder.partition("Penalties\n")[0] if separator else ""
    roster = {}
    for number, name in re.findall(
        r"^(\d{1,3})\s+(.+?)\s+(?:(?:A|C)\s+)?(?:GK|D|F)\b",
        roster_text,
        re.M,
    ):
        roster[number] = gamesheet_player_name(name.strip())
    canonical_names = {comparable_name(name): name for name in (player_names or [])}
    scorers = []
    for goal_time, number, suffix in re.findall(
        r"^\d+\s+(\d{2}:\d{2})\s+(\d{1,3})([^\n]*)$",
        goals_text,
        re.M,
    ):
        scorer = roster.get(number)
        if not scorer:
            continue
        scorer = GAMESHEET_NAME_CORRECTIONS.get(scorer, canonical_names.get(comparable_name(scorer), scorer))
        is_shootout = bool(re.search(r"\bPS\b", suffix)) or int(goal_time.split(":", 1)[0]) >= 65
        scorers.append({
            "team": team,
            "scorer": scorer,
            "time": goal_time,
            "period": "Shootout" if is_shootout else period_for_time(goal_time),
        })
    return scorers


def apply_preseason_hub_results(games: list[dict], hub_games: list[dict], source_url: str) -> None:
    """Use the official EIHL hub as a fast score fallback for Steelers friendlies."""
    results_by_fixture = {
        (game["date"], game["home"], game["away"]): game
        for game in hub_games
        if game.get("date") and game.get("home") and game.get("away")
    }
    for game in games:
        if game.get("competition") != "Pre-season":
            continue
        game_date = datetime.fromisoformat(game["starts_at"]).date().isoformat()
        result = results_by_fixture.get((game_date, game["home"], game["away"]))
        if not result:
            continue
        if result.get("gamesheet_url"):
            game["gamesheet_url"] = result["gamesheet_url"]
        if game.get("complete"):
            continue
        game.update({
            "score": f'{result["home_score"]}–{result["away_score"]}',
            "complete": True,
            "live": False,
            "status": "Final (SO)" if result.get("overtime") else "Final",
            "scorers": game.get("scorers", []),
            "finished_at": (datetime.fromisoformat(game["starts_at"]) + timedelta(hours=3)).isoformat(),
            "featured_until": (datetime.fromisoformat(game["starts_at"]) + timedelta(hours=4)).isoformat(),
            "details_url": source_url or game.get("details_url"),
        })


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


def comparable_name(name: str) -> str:
    """Make minor official-source spelling differences safe to match."""
    import unicodedata
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", plain.lower()).replace("matthew", "matt")


def parse_eihl_numbers() -> dict[str, str]:
    """Read numbers if the EIHL's 2026/27 team roster has been populated."""
    page = fetch(ROSTER_PAGE)
    numbers: dict[str, str] = {}
    for row in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", page):
        cells = [text(cell) for cell in re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)]
        if len(cells) < 3 or not re.fullmatch(r"\d{1,3}", cells[0]):
            continue
        name = re.sub(r"^(CAN|USA|GBR|FIN|SWE|CZE|SVK|NOR|DEN)\s*", "", cells[1]).strip()
        if name:
            numbers[comparable_name(name)] = cells[0]
    return numbers


def parse_roster(previous: dict | None = None) -> dict:
    """Build the live roster from the official EIHL tracker, retaining safe data on failure."""
    try:
        page = fetch(ROSTER_TRACKER)
        section = re.search(r"<p><b>Sheffield Steelers[\s\S]*?</p>", page, re.I)
        if not section:
            raise ValueError("Sheffield roster section was not found")
        lines = [text(part) for part in re.split(r"<br\s*/?>", section.group(0), flags=re.I)]
        labels = {"Goalies": "goalies", "Defenseman": "defence", "Forwards": "forwards"}
        groups = {"goalies": [], "defence": [], "forwards": []}
        try:
            live_numbers = parse_eihl_numbers()
        except Exception as error:
            print(f"EIHL shirt numbers unavailable; roster names will still refresh: {error}")
            live_numbers = {}
        for line in lines:
            for label, key in labels.items():
                if not line.startswith(label + ":"):
                    continue
                for raw_name in line.split(":", 1)[1].split(","):
                    name = raw_name.replace("*", "").strip()
                    if name:
                        number = live_numbers.get(comparable_name(name), CONFIRMED_NUMBERS.get(name))
                        groups[key].append({"name": name, "number": number})
        if sum(map(len, groups.values())) < 12:
            raise ValueError("Official roster looked incomplete")
        return {"source": "Official EIHL roster tracker", "source_url": urllib.parse.urljoin(BASE, ROSTER_TRACKER), "groups": groups}
    except Exception as error:
        if previous and previous.get("groups"):
            print(f"Roster refresh unavailable; retained last good roster: {error}")
            return previous
        raise


def main() -> None:
    now = datetime.now(timezone.utc)
    previous_payload = {}
    if OUTPUT.exists():
        try:
            previous_payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    repository_payload = previous_payload
    try:
        published_payload = json.loads(fetch(LIVE_DATA_URL))
        published_at = datetime.fromisoformat(published_payload.get("generated_at", "1970-01-01T00:00:00+00:00"))
        local_at = datetime.fromisoformat(previous_payload.get("generated_at", "1970-01-01T00:00:00+00:00"))
        if published_at > local_at:
            previous_payload = published_payload
    except Exception as error:
        print(f"Published-data carry-forward unavailable; using repository data: {error}")
    roster = parse_roster(previous_payload.get("roster"))
    player_names = [player["name"] for group in roster["groups"].values() for player in group]
    games_by_id: dict[str, dict] = {}
    for season_id, competition in SEASONS.items():
        for game in parse_schedule(season_id, competition):
            games_by_id[game["id"]] = game
    competitive_start = min(datetime.fromisoformat(game["starts_at"]) for game in games_by_id.values())
    for game in parse_preseason_fixtures(player_names):
        if datetime.fromisoformat(game["starts_at"]) < competitive_start:
            games_by_id[game["id"]] = game
    games = sorted(games_by_id.values(), key=lambda game: game["starts_at"])

    previous_preseason = previous_payload.get("preseason", {})
    preseason_source_url = previous_preseason.get("source_url", "")
    preseason_games_by_key = {
        (game["date"], game["home"], game["away"]): game
        for game in previous_preseason.get("games", [])
        if game.get("date") and game.get("home") and game.get("away")
    }
    try:
        official_preseason_games, preseason_source_url = parse_preseason_hub(preseason_source_url)
        for game in official_preseason_games:
            preseason_games_by_key[(game["date"], game["home"], game["away"])] = game
    except Exception as error:
        print(f"Pre-season hub refresh unavailable; retained last good table: {error}")
    apply_preseason_hub_results(games, list(preseason_games_by_key.values()), preseason_source_url)

    live_window = False
    for game in games:
        seconds_from_start = (now - datetime.fromisoformat(game["starts_at"]).astimezone(timezone.utc)).total_seconds()
        if -15 * 60 <= seconds_from_start <= 12 * 60 * 60:
            live_window = True
        recover_recent_result = not game["complete"] and 12 * 60 * 60 < seconds_from_start <= 7 * 24 * 60 * 60
        if game["competition"] != "Pre-season" and (-15 * 60 <= seconds_from_start <= 12 * 60 * 60 or recover_recent_result):
            try:
                game.update(parse_eihl_game_details(game))
            except Exception as error:
                print(f"Recent game detail unavailable for {game['id']}: {error}")
    live_game = next((game for game in games if game.get("live")), None)
    upcoming = [game for game in games if not game["complete"] and datetime.fromisoformat(game["starts_at"]).astimezone(timezone.utc) >= now]
    add_ticket_links(upcoming)
    stored_exact_tickets = {
        game["id"]: game["ticket_url"]
        for payload in (repository_payload, previous_payload)
        for game in payload.get("all_upcoming", [])
        if game.get("id") and game.get("ticket_exact") and game.get("ticket_url")
    }
    for game in upcoming:
        if not game.get("ticket_exact") and game["id"] in stored_exact_tickets:
            game["ticket_url"] = stored_exact_tickets[game["id"]]
            game["ticket_exact"] = True
    results = [game for game in games if game["complete"]]
    results.sort(key=lambda game: game["starts_at"], reverse=True)
    previous_results = {
        game["id"]: game for game in previous_payload.get("results", []) if game.get("id")
    }
    for game in results:
        previous = previous_results.get(game["id"], {})
        for key in ("scorers", "finished_at", "featured_until", "gamesheet_url", "highlights"):
            if not game.get(key) and previous.get(key):
                game[key] = previous[key]
    for game in results[:3]:
        missing_detail = not game.get("scorers") or any(
            goal.get("time") == "Time unavailable" for goal in game.get("scorers", [])
        )
        if game.get("competition") == "Pre-season" and game.get("gamesheet_url") and missing_detail:
            try:
                gamesheet_scorers = parse_gamesheet_scorers(game["gamesheet_url"], player_names=player_names)
                if gamesheet_scorers:
                    game["scorers"] = gamesheet_scorers
            except Exception as error:
                print(f"Official gamesheet detail unavailable for {game['id']}: {error}")

    official_videos = []
    for source, feed_url in OFFICIAL_VIDEO_FEEDS:
        try:
            official_videos.extend(parse_video_feed(source, feed_url))
        except Exception as error:
            print(f"{source} highlights feed unavailable; retained existing links: {error}")
    for game in results[:6]:
        if game.get("highlights"):
            continue
        highlight = match_highlight_video(game, official_videos)
        if not highlight and game.get("details_url"):
            try:
                highlight = embedded_youtube_video(game["details_url"])
            except Exception as error:
                print(f"Embedded highlights unavailable for {game['id']}: {error}")
        if highlight:
            game["highlights"] = highlight
    if results and results[0]["competition"] != "Pre-season" and not results[0].get("scorers"):
        try:
            results[0].update(parse_eihl_game_details(results[0]))
        except Exception as error:
            print(f"Last-game detail unavailable for {results[0]['id']}: {error}")
    recent_final = next((
        game for game in results
        if game.get("featured_until") and datetime.fromisoformat(game["featured_until"]).astimezone(timezone.utc) > now
    ), None)
    featured_game = live_game or recent_final

    for game in results:
        if game["competition"] != "Pre-season":
            continue
        home_score, away_score = (int(value) for value in game["score"].split("–"))
        game_date = datetime.fromisoformat(game["starts_at"]).date().isoformat()
        key = (game_date, game["home"], game["away"])
        previous_friendly = preseason_games_by_key.get(key, {})
        preseason_games_by_key[key] = {
            "id": game["id"], "date": game_date, "home": game["home"], "away": game["away"],
            "home_score": home_score, "away_score": away_score,
            "overtime": previous_friendly.get("overtime", False),
            "gamesheet_url": game.get("gamesheet_url") or previous_friendly.get("gamesheet_url"),
        }
    preseason_games = sorted(preseason_games_by_key.values(), key=lambda game: (game["date"], game["home"], game["away"]))
    preseason_table = build_preseason_table(preseason_games)

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
        "position": steelers_row["position"] if steelers_row and steelers_row["played"] > 0 else None,
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
        "live_window": live_window,
        "live_game": live_game,
        "featured_game": featured_game,
        "next_game": upcoming[0] if upcoming else None,
        "last_game": results[0] if results else None,
        "upcoming": upcoming[:6],
        "all_upcoming": upcoming,
        "results": results,
        "standings": {"league": league, "cup": cup, "preseason": preseason_table},
        "preseason": {
            "source": "Official EIHL pre-season hub",
            "source_url": preseason_source_url,
            "games": preseason_games,
            "table": preseason_table,
        },
        "snapshot": snapshot,
        "roster": roster,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    OUTPUT.write_text(serialized + "\n", encoding="utf-8")
    JS_OUTPUT.write_text("window.STEELERS_DATA = " + serialized + ";\n", encoding="utf-8")
    print(f"Updated {OUTPUT}: {len(upcoming)} upcoming, {len(results)} completed")


if __name__ == "__main__":
    main()
