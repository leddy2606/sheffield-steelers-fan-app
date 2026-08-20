# Steel City Match Centre

An unofficial, installable Sheffield Steelers fan app. Fixtures, completed results, league standings, Challenge Cup standings, and the season snapshot are refreshed from the public EIHL website every three hours.

Current local version: **1.3.0**. See `CHANGELOG.md` for the recoverable version history.

## Free hosting model

The included GitHub Pages workflow uses only free services for a public repository:

- GitHub Pages hosts the static PWA.
- GitHub Actions runs `scripts/update_data.py` every three hours.
- The updater writes `data/app-data.json` and `data/app-data.js`.
- The app keeps the last successful update available offline.

No paid API, database, live-score provider, domain, or server is required. GitHub Pages must be enabled with **GitHub Actions** as its source after the repository is first created.

The app is unofficial and should remain for personal/fan use. The public EIHL pages remain the authoritative source.
