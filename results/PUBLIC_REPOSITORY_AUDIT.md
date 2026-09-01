# Public Repository Audit

**Date:** 2026-09-01
**Scope:** files intended for the open-source v0.1 release

## Result

**PASS WITH CONDITIONS**

The tracked release scope contains no detected credentials, bearer tokens,
private Windows paths, PCAP content, raw/processed datasets, or model
checkpoints. No tracked file exceeded 10 MB. The working tree does contain
local ignored datasets, PCAP archives, model artifacts, and generated reports;
they remain excluded by `.gitignore` and must not be staged.

## Checks performed

- Reviewed `git status` and the tracked-file boundary.
- Confirmed raw and processed data, PCAP/PCAPNG, and model checkpoint patterns
  are ignored.
- Confirmed the local root CSV is ignored and is not part of the release.
- Scanned release-scope text for private Windows paths and common credential
  patterns; none were found.
- Confirmed the project-owned code license is MIT.
- Confirmed dataset, PCAP, and model artifacts are separately governed and are
  not redistributed by this repository.

## Conditions for maintainers

Review staged files before every public push. Do not add `.env` files,
credentials, traffic captures, data archives, checkpoints, or generated local
state. Dataset and model acquisition must follow its own license and access
rules. The MIT license applies only to project-owned code and documentation
where the project has the right to license it.
