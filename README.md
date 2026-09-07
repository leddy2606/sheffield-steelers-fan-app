# Steel City Match Centre

An unofficial, installable Sheffield Steelers fan app. It includes near-live competitive scores, fixtures, expandable match history and reports, standings, roster data and the season snapshot from official sources.

Current local version: **1.14.1**. See `CHANGELOG.md` for the recoverable version history.

## Free hosting model

The included GitHub Pages workflow uses only free services for a public repository:

- GitHub Pages hosts the static PWA.
- GitHub Actions checks for an active match every ten minutes and performs the normal full refresh every three hours.
- Every open app checks for newly published data immediately and every two minutes.
- Match-window deployments read live competitive scores and scorer details from the official EIHL Gamecentre.
- Pre-season scores use official Sheffield Steelers match reports, with the official EIHL pre-season hub as a fallback when a club report is delayed.
- Official EIHL game-sheet PDFs provide a second detailed source for scorer, time and period information.
- Source priority is Steelers report, EIHL game sheet, then the EIHL roundup as a score-only safety net.
- Match reports automatically check the free official Steelers YouTube feed and official report embeds for highlights.
- Until a matching official video is published, the app shows a clean pending message and keeps checking.
- Every upcoming fixture expands to offer its own calendar download and official ticket link.
- Ticket links automatically use an exact official event page when one can be identified, otherwise the home club's official ticket page.
- The unofficial pre-season form table is calculated from the official league-wide EIHL pre-season hub.
- The updater writes `data/app-data.json` and `data/app-data.js`.
- The app keeps the last successful update available offline.

No paid API, database, third-party live-score provider, domain, or server is required. GitHub Pages must be enabled with **GitHub Actions** as its source after the repository is first created.

The app is unofficial and should remain for personal/fan use. The public EIHL pages remain the authoritative source.
