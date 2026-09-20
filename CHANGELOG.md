# Version history

## 1.17.0 — 20 September 2026

- Increased match-window checks to GitHub's free five-minute scheduling limit.
- Avoided unnecessary EIHL requests and deployments outside match windows; regular data still refreshes every three hours.
- Added a minimalist live-only timeline for three periods, two breaks, overtime and shootout.
- Clearly labels timeline movement as an estimate based on the latest official EIHL phase update.

## 1.16.0 — 20 September 2026

- Rebuilt the season snapshot around automatic competition views.
- Added All competitions, EIHL League, Challenge Cup and Pre-season filters.
- Each view now recalculates position/scope, games, points, wins, goals and recent form from its matching table and results.

## 1.15.0 — 20 September 2026

- Fixed completed overtime games being mistaken for matches still in progress.
- Added a seven-day recovery check for missing results, so delayed schedule scores do not make games disappear.
- Offset the free ten-minute GitHub schedule to reduce delayed or dropped runs at busy times.

## 1.14.1 — 7 September 2026

- Retains verified exact event links when Ticketmaster blocks an automated refresh, instead of downgrading them.

## 1.14.0 — 7 September 2026

- Made every upcoming fixture expandable with its own add-to-calendar action.
- Added automatically refreshed official ticket links for home and away games.
- Uses the exact official event listing when available, with the home club's official ticket page as a safe fallback.

## 1.13.0 — 7 September 2026

- Added automatically discovered official YouTube highlights inside expandable match reports.
- Added a polished pending state while a match video has not yet been uploaded.
- Added automatic retrying through the free Steelers YouTube feed and official match-report embeds.

## 1.12.0 — 7 September 2026

- Added automatic reading of official EIHL game-sheet PDFs for exact scorers, goal times and periods.
- Established a free fallback chain: Steelers report, EIHL game sheet, then EIHL roundup score.
- Filled the complete scoring details for both Manchester Storm pre-season games.

## 1.11.0 — 7 September 2026

- Added the official EIHL pre-season hub as a score fallback when a Steelers match report is delayed.
- Kept Steelers match reports as the richer source for scorers, periods and match details.
- Confirmed the updater and hosting still use only free public sources and GitHub Pages.

## 1.10.0 — 30 August 2026

- Showed the latest three completed games before hiding older results behind the history expander.
- Removed the expander automatically until a fourth completed game exists.
- Added an unofficial pre-season form table calculated from the official league-wide EIHL pre-season hub.
- Made the page check immediately on opening and every two minutes thereafter, while carrying the last published data into every refresh.

## 1.9.0 — 30 August 2026

- Synchronized the mobile bottom navigation with the section currently being viewed.
- Kept tap-to-jump navigation and added accessible current-location state.
- Added a subtle highlight transition when the active section changes.

## 1.8.0 — 30 August 2026

- Fixed pre-season results whose score appears inside the official report rather than its headline.
- Added automatic same-day report matching and a 12-hour post-game checking window.
- Combined Latest Results and Last Game into one expandable Results & Match Reports section.
- Kept the complete season history, with score, home/away status, scorers, goal times, periods and official report links when available.

## 1.7.0 — 30 August 2026

- Made the top match card switch automatically between Next Game, Live Game and Final Score.
- Kept the official final score featured for one hour after the final whistle.
- Added exact EIHL end-time parsing with a safe pre-season fallback.

## 1.6.0 — 30 August 2026

- Added an expandable full-season fixture list beneath the next six games.
- Added a live remaining-game count while keeping the compact default view.

## 1.5.0 — 30 August 2026

- Added near-live competitive scores from the official EIHL Gamecentre.
- Added automatic on-page data checks while the app remains open.
- Added a Last Game tab with result, opponent, home/away status and Steelers scorer timeline.
- Added ten-minute match-window publishing while retaining the normal three-hour refresh.

## 1.4.1 — 30 August 2026

- Fixed completed pre-season games disappearing instead of becoming results.
- Added automatic score detection from official Steelers match reports.
- Added the Cardiff Devils 4–3 Sheffield Steelers result from 29 August.

## 1.4.0 — 20 August 2026

- Added automatic three-hour squad updates from the official EIHL roster tracker.
- Added confirmed shirt numbers, with new EIHL numbers picked up automatically.
- Added last-known-good roster protection if an official source is temporarily unavailable.

## 1.3.1 — 20 August 2026

- Replaced the placeholder browser and installed-app icon with the official Sheffield Steelers crest.
- Added the official crest to the app header.
- Refreshed the offline cache so existing installations receive the corrected branding.

## 1.3.0 — 20 August 2026

- Preserved the approved automatic-update build as the recoverable baseline.
- Added clear orange home and blue away fixture treatments.
- Replaced the placeholder roster with the current 2026/27 squad.
- Prevented an unplayed, alphabetical table from showing Sheffield as “10th”.
- Added project housekeeping and validation safeguards.

## 1.2.0 — 20 August 2026

- Added free three-hour fixture, result, and standings refreshes.
- Added official pre-season fixtures and a last-updated indicator.
- Added offline fallback and free GitHub Pages publishing workflow.

## 1.1.0 — 19 August 2026

- Added all ten EIHL team crests.
- Added team crests throughout fixtures, results, and standings.
- Corrected mixed-colour form display.

## 1.0.0 — 19 August 2026

- Created the first mobile-first, installable Steelers dashboard.
