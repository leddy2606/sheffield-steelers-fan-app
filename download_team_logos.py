import json
import ssl
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
import time

TEAMS = {
    "belfast-giants": ("Belfast Giants", "belfast giants"),
    "cardiff-devils": ("Cardiff Devils", "cardiff devils"),
    "coventry-blaze": ("Coventry Blaze", "coventry blaze"),
    "dundee-stars": ("Dundee Stars", "dundee stars"),
    "fife-flyers": ("Fife Flyers", "fife flyers"),
    "glasgow-clan": ("Glasgow Clan", "glasgow clan"),
    "guildford-flames": ("Guildford Flames", "guilford flames"),
    "manchester-storm": ("Manchester Storm (2015–)", "manchester storm"),
    "nottingham-panthers": ("Nottingham Panthers", "nottingham panthers"),
    "sheffield-steelers": ("Sheffield Steelers", "sheffield steelers"),
}

ctx = ssl._create_unverified_context()
headers = {"User-Agent": "SteelCityMatchCentre/1.0 (fan app asset fetch)"}
out = Path("assets/teams")
out.mkdir(parents=True, exist_ok=True)


def api(params):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, context=ctx, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            time.sleep(4 * (attempt + 1))


import re

standings_request = urllib.request.Request(
    "https://www.eliteleague.co.uk/standings", headers=headers
)
with urllib.request.urlopen(standings_request, context=ctx, timeout=30) as response:
    standings_html = response.read().decode("utf-8", "ignore")

matches = re.findall(
    r'data-src="([^"]*/photo/team/[^"]+)"[\s\S]{0,1500}?'
    r'href="/team/[^"]+"[\s\S]{0,400}?([^<]+)</a>',
    standings_html,
)
print(f"FOUND {len(matches)} team crest references")
name_to_slug = {
    page_title.replace(" (2015–)", "").lower(): slug
    for slug, (page_title, _) in TEAMS.items()
}
for source, raw_name in matches:
    team_name = " ".join(raw_name.split()).lstrip("> ")
    slug = name_to_slug.get(team_name.lower())
    if not slug:
        continue
    source_url = urllib.parse.urljoin("https://www.eliteleague.co.uk", source)
    extension = Path(urllib.parse.urlparse(source_url).path).suffix.lower() or ".png"
    destination = out / f"{slug}{extension}"
    request = urllib.request.Request(source_url, headers=headers)
    with urllib.request.urlopen(request, context=ctx, timeout=30) as response:
        destination.write_bytes(response.read())
    print(f"OK {team_name}: {destination.name}")
