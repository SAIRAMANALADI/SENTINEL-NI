# Contributing to Sentinel / NI

Contributions should preserve the frozen data and model contracts unless a
separate scientific review explicitly approves a versioned change.

Before opening a pull request:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Keep changes focused, add tests for new behavior, and document operational
limitations. Never commit datasets, PCAPs, model checkpoints, credentials,
payloads, or generated local artifacts. Do not describe Forecast Score as a
calibrated probability, candidate sources as attackers, or recommendations
as autonomous enforcement.
