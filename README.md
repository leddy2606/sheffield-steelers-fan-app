# Steel City Match Centre

An unofficial, installable Sheffield Steelers fan app. It includes near-live competitive scores, fixtures, results, a Last Game scorer recap, standings, roster data and the season snapshot from official sources.

Current local version: **1.6.0**. See `CHANGELOG.md` for the recoverable version history.

## Free hosting model

The included GitHub Pages workflow uses only free services for a public repository:

- GitHub Pages hosts the static PWA.
- GitHub Actions checks for an active match every ten minutes and performs the normal full refresh every three hours.
- Match-window deployments read live competitive scores and scorer details from the official EIHL Gamecentre.
- Pre-season results and scorers use official Sheffield Steelers match reports when available.
- The updater writes `data/app-data.json` and `data/app-data.js`.
- The app keeps the last successful update available offline.

No paid API, database, third-party live-score provider, domain, or server is required. GitHub Pages must be enabled with **GitHub Actions** as its source after the repository is first created.

The app is unofficial and should remain for personal/fan use. The public EIHL pages remain the authoritative source.
