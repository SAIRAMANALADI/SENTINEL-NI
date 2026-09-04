# Phase AA — Independent External Validation

Validation date: 2026-09-04  
Project: Sentinel / NI (`SIH26-26153`)

Final classification: **PUBLIC LAUNCH READY — EXTERNAL VALIDATION PENDING**

Phase AA did not have access to an unrelated validator, independently
controlled host, clean VM, Linux host, or public staging endpoint. No local
simulation, replay, mock telemetry, or same-machine second user is counted as
independent validation. This report records the prepared handoff, candidate
identity, local regression evidence inherited from Phase Z, and the remaining
external gates.

## 1. Validator identity/category

**Status: NOT TESTED**

No independent validator participated in this run. The current environment is
the implementation environment and therefore cannot satisfy the independent
validator requirement.

## 2. Environment

**Status: VERIFIED** for the local environment record; **Status: NOT TESTED**
for an independent environment.

- OS: Windows development host
- Python: 3.14
- Node: local Node/npm frontend toolchain; version not used as external evidence
- Browser: no independent browser session
- Docker: Docker Desktop available; Compose config smoke only
- Network: local development network; no independent network environment
- Central host: local host only
- Sensor host: local host only
- TLS mode: no public TLS endpoint tested

## 3. Candidate identity

**Status: VERIFIED** for the recorded local candidate.

- Git commit: `41dbec11a433370e28aa083274202b1f92ddd5c5`
- Branch: `main`; `origin/main` resolves to the same commit
- Working-tree state: 104 entries before this report was added; 57 modified,
  47 untracked, and 0 staged
- Working-tree diff hash inherited from the Phase Z freeze:
  `ca3911bcd970355150b00b1cf007da6acf7bf2b02f8893baeff3ad068e44808d`
- Wheel SHA256:
  `6C3B89ED8FED44B549DF2BB0859B74976B7872D75A8784FEAB52DEB024B21768`
- Sdist SHA256:
  `C947138D69D8462EFA08218957F719864C12A6D32290756627C0FB56D4E6286C`

The diff hash covers the candidate files recorded at the Phase Z freeze and
excludes the Phase Z report; this Phase AA report is also excluded from the
identity record. The public annotated `v0.1.0` remains unchanged and does not
identify the dirty working-tree candidate.

## 4. Installation

**Status: NOT TESTED** for independent installation; **Status: VERIFIED** for
the prior local package smoke.

The documented package smoke installed the wheel into the local virtual
environment, `sentinel-agent --version` returned `0.2.0`, help listed the
documented command groups, and `pip check` passed. A clean independent
checkout has not executed the handoff package.

## 5. Central startup

**Status: NOT TESTED** independently; **Status: VERIFIED** for the documented
startup contract and local Compose configuration.

No independent Central process or host was started for this phase. The
quickstart provides both direct-Uvicorn TLS and trusted reverse-proxy paths.

## 6. Dashboard authentication

**Status: NOT TESTED** independently; **Status: VERIFIED** for local
implementation and prior authorization smoke evidence.

Unauthenticated access, role-token configuration, logout, session expiry, and
privileged-action boundaries were not exercised by an unrelated browser in
this phase. No authentication bypass was introduced or claimed.

The available local browser/runtime was stale relative to the candidate: its
session route returned `404` and its UI did not contain the current Live entry.
That runtime was excluded from candidate and external evidence.

## 7. Sensor registration

**Status: NOT TESTED** independently; **Status: VERIFIED** for the documented
admin-controlled enrollment and one-time registration contract.

No independently operated sensor host created or registered a sensor.

## 8. Heartbeat

**Status: NOT TESTED** independently; **Status: VERIFIED** in the existing
local contract tests.

Fresh heartbeat evidence from an unrelated sensor host is absent.

## 9. Telemetry

**Status: NOT TESTED** independently; **Status: VERIFIED** in existing local
contract evidence.

No external packet capture or independent telemetry delivery evidence is
available.

## 10. Live capture

**Status: NOT TESTED**

No independent host captured actual network traffic. Replay, mock telemetry,
and canned state are expressly excluded from this gate.

## 11. L=10

**Status: NOT TESTED** independently; **Status: VERIFIED** as a frozen local
contract.

The required contiguous live history was not produced by an unrelated
environment.

## 12. K=5

**Status: NOT TESTED** independently; **Status: VERIFIED** as a frozen local
contract.

No independent live run produced the five-step forecast.

## 13. Five forecast horizons

**Status: NOT TESTED** independently; **Status: VERIFIED** as a frozen local
contract.

The documented horizons are +10s, +20s, +30s, +40s, and +50s. Independent
dashboard rendering evidence is unavailable.

## 14. Candidate Source

**Status: NOT TESTED** independently; **Status: VERIFIED** for the documented
source-attribution wording.

The handoff instructs the validator to verify Candidate Source without
interpreting it as attacker identity.

## 15. Mitigation

**Status: NOT TESTED** independently; **Status: VERIFIED** for the documented
recommendation-only safety boundary.

The handoff uses “Mitigation Recommendation” and does not claim automatic
blocking.

## 16. Restart/recovery

**Status: NOT TESTED** independently; **Status: VERIFIED** for the documented
restart procedure and existing local contracts.

No independent agent restart or Central restart was observed.

## 17. Central outage/retry

**Status: NOT TESTED** independently; **Status: PARTIAL** for local
implementation evidence.

No external outage start/end timestamps, buffering observation, retry/reconnect
observation, or recovery data-loss record exists.

## 18. Customer-path independence

**Status: NOT TESTED** independently; **Status: VERIFIED** as an architectural
requirement and documented test procedure.

No separate customer application endpoint was exercised concurrently with an
independent Sentinel sensor. The required topology remains direct customer
traffic to the application server while Sentinel observes telemetry out of
band.

## 19. TLS

**Status: NOT TESTED** for public TLS; **Status: PARTIAL** for local security
evidence.

The documented direct-TLS and trusted-proxy configurations exist, but no public
certificate, hostname validation, invalid-certificate, hostname-mismatch,
HTTP-rejection, or forged-forwarded-header test was run against an independent
endpoint.

## 20. TruffleHog

**Status: NOT VERIFIED** — the tool was not installed or run in this
environment.

Bounded package-content scanning and the strict release audit remain local
evidence only; they do not substitute for TruffleHog.

## 21. Linux

**Status: NOT TESTED**

The quickstart contains a Linux installation path, but no genuine Linux agent
host executed it.

## 22. Multi-host

**Status: NOT TESTED**

No separate Central and sensor hosts under independent control were deployed.

## 23. Five-sensor status

**Status: NOT TESTED**

Five genuinely separate sensor identities or environment instances were not
available and no five-sensor claim is made.

## 24. 30-minute soak

**Status: NOT TESTED**

No genuine 30-minute external soak run was performed.

## 25. Failures

**Status: VERIFIED** for the gate outcome.

There is no external execution failure to triage because the independent pilot
did not start. The blocking condition is missing independent environment and
validator evidence, not an observed P0/P1 product defect.

The backend review raised an unverified P1 risk around concurrent same-sensor
telemetry: the sequence check, runtime mutation, and registry commit are
separate operations. The available probe demonstrated an ordering conflict,
but did not demonstrate runtime corruption or a customer-visible failure, so
no candidate patch was justified under the evidence-only freeze.

Historical evidence also contains an Npcap/live-capture wording conflict and
older Windows cleanup evidence that is superseded by later local claims. These
are not independent Phase AA evidence and remain documentation-validation
follow-up.

## 26. Fixes

**Status: VERIFIED**

No Phase AA P0/P1 fix was required or applied. Candidate Z was not silently
modified under test. P2/P3 residuals and unverified environment gates remain
post-release or external-validation work; they do not authorize feature creep
or changes to the ML pipeline, forecast policy, authentication, or routing.

## 27. Final regression

**Status: VERIFIED** for the Phase AA local regression run; **Status: NOT
TESTED** in an independent environment.

The frozen implementation was rerun locally in Phase AA; these results remain
same-machine evidence and do not qualify as independent validation:

- `pytest`: 323 passed, 2 warnings
- Frontend typecheck: PASS
- Frontend build: PASS
- Wheel and sdist build: PASS
- `pip check`: PASS
- Strict release audit: PASS
- Package audit: PASS
- `git diff --check`: PASS
- Docker Compose configuration: PASS

No release-critical fix was made in Phase AA, so no new regression run was
needed after a code change.

## 28. Remaining limitations

**Status: BLOCKED** for unconditional `PUBLIC LAUNCH READY`.

The required independent validator, external installation, real live capture,
public TLS, TruffleHog, Linux, multi-host, five-sensor, resilience, customer-
path, and soak evidence remain outstanding. The handoff package is prepared,
but documentation readiness is not execution evidence. The result template
also does not contain a dedicated independence attestation or candidate-
immutability field; this coordinator report supplies those declarations.

## 29. Release recommendation

**Status: VERIFIED** for the conditional recommendation.

Retain the classification **PUBLIC LAUNCH READY — EXTERNAL VALIDATION
PENDING**. Do not publish, push, mutate `v0.1.0`, or claim unconditional public
launch readiness. An unrelated validator must execute the quickstart against
the identified candidate and submit the result template. If a genuine P0/P1
defect appears, preserve this candidate as Candidate A, create Candidate B with
the scoped fix, re-identify it, and rerun affected validation. If the core
workflow passes in the independent environment and no P0/P1 defect remains,
the release owner may re-evaluate the classification.

### Safe next action

Provide the repository or approved artifact hashes and
[`EXTERNAL_VALIDATION_QUICKSTART.md`](EXTERNAL_VALIDATION_QUICKSTART.md) to an
unrelated validator. The validator should return the completed
[`EXTERNAL_VALIDATION_RESULT_TEMPLATE.md`](EXTERNAL_VALIDATION_RESULT_TEMPLATE.md)
with safe output, timestamps, and no credentials, private keys, raw packet
captures, customer payloads, or private filesystem paths.
