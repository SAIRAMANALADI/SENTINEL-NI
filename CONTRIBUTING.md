# Contributing to Sentinel / NI

Contributions should preserve the frozen data and model contracts unless a
separate scientific review explicitly approves a versioned change.

Before opening a pull request:

```bash
python -m pip install -r requirements-dev.txt
python scripts/release_audit.py
python -m pytest -q
```

For frontend changes, also run from `frontend/`:

```bash
npm ci
npm run typecheck
npm run build
```

For packaging changes, run `python -m build --wheel --sdist` and inspect the
wheel and source archive contents. Documentation-only changes should still
run the release audit and link checks. Environment-dependent checks requiring
Docker Desktop, Npcap/libpcap, a real network interface, TLS termination, or
multiple hosts must be labeled as such; do not report them as CI coverage.

Pull requests should explain the user-visible change, the verification run,
and any known limitation. Keep the frozen 17-feature, target, L=10, K=5, and
threshold contracts unchanged unless a separately reviewed versioned change
is intended.

Keep changes focused, add tests for new behavior, and document operational
limitations. Never commit datasets, PCAPs, model checkpoints, credentials,
payloads, or generated local artifacts. Do not describe Forecast Score as a
calibrated probability, candidate sources as attackers, or recommendations
as autonomous enforcement.
