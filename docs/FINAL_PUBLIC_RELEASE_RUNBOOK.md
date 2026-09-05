# Sentinel Final Public Release Runbook

Project: Sentinel / NI (`SIH26-26153`)
Current candidate base: `db8886fa2d25867b34d3d658901f32ef16e638f8` plus the
uncommitted Phase AB working-tree delta
Current classification: **PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**

This runbook is a human release decision record. It does not authorize
publication by itself. Do not use the implementation/development machine as
the independent validator, and do not move or delete the existing annotated
`v0.1.0` tag, which targets an earlier commit.

## Gate checklist

- [ ] NOT VERIFIED — External validation completed by an unrelated validator.
- [ ] NOT VERIFIED — Candidate frozen after final review.
- [x] VERIFIED — Local final regression is green: `326 passed, 2 warnings`.
- [x] VERIFIED — Security scan status recorded; TruffleHog remains
  `NOT VERIFIED — TOOL NOT INSTALLED`.
- [x] VERIFIED — TLS limitations and required public checks recorded.
- [x] VERIFIED — Candidate working-tree artifact hashes rebuilt and recorded.
- [x] VERIFIED — Git provenance and existing tag relationship verified.
- [ ] NOT VERIFIED — Final release commit created.
- [ ] NOT VERIFIED — Tag strategy approved by the release owner.
- [ ] NOT VERIFIED — GitHub release created.
- [ ] NOT VERIFIED — Post-publication verification complete.

## Required pre-publication gates

1. An unrelated validator completes [`EXTERNAL_VALIDATION_QUICKSTART.md`](EXTERNAL_VALIDATION_QUICKSTART.md)
   and returns [`EXTERNAL_VALIDATION_RESULT_TEMPLATE.md`](EXTERNAL_VALIDATION_RESULT_TEMPLATE.md).
2. The release owner reviews all `NOT VERIFIED` and `BLOCKED` items in the
   Phase AB report and accepts the evidence boundary.
3. The owner selects the exact source files for the release commit, verifies
   the worktree, and rebuilds artifacts from that commit.
4. The owner confirms the new artifact hashes and runs the strict release
   audit, tests, frontend checks, package checks, and Compose checks.

## Exact publication procedure

Run only after the gates above are complete and the owner approves publication.
The existing `v0.1.0` is preserved. Because it points to an earlier commit,
the next release must use a new version and tag (`0.1.1` / `v0.1.1`); never
force-move `v0.1.0`.

```powershell
git status --short
git diff --check

# Update approved package/release metadata and notes from 0.1.0 to 0.1.1.
# Review and stage only the approved release files.
git add <approved-release-files>
git diff --cached --check
git commit -m "Release Sentinel / NI v0.1.1"
$releaseCommit = git rev-parse HEAD
$env:SOURCE_DATE_EPOCH = (git show -s --format=%ct $releaseCommit)

py -m build --wheel --sdist
py scripts/release_audit.py --strict
Get-FileHash .\dist\sih26_26153-0.1.1-py3-none-any.whl -Algorithm SHA256
Get-FileHash .\dist\sih26_26153-0.1.1.tar.gz -Algorithm SHA256
py -m pip install --requirement requirements-release.txt
py -m twine check .\dist\sih26_26153-0.1.1-*

git tag -a v0.1.1 -m "Sentinel / NI v0.1.1"
git push origin main
git push origin v0.1.1
gh release create v0.1.1 .\dist\sih26_26153-0.1.1-* docs\RELEASE_ARTIFACT_SHA256SUMS.txt --title "Sentinel / NI v0.1.1" --notes-file docs\RELEASE_NOTES.md
py -m twine upload .\dist\sih26_26153-0.1.1-*

git ls-remote origin refs/heads/main refs/tags/v0.1.0 refs/tags/v0.1.1
gh release view v0.1.1
```

Do not run this procedure during Phase AB.

## Post-publication verification

Confirm the release commit, `v0.1.1` tag object, GitHub release assets, PyPI
metadata, artifact hashes, README installation path, and the preserved
`v0.1.0` tag. Record URLs and timestamps without recording credentials.
