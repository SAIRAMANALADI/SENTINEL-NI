# Issue Triage

This lightweight policy keeps first-user feedback reproducible and safe. It
does not promise response times or a service-level agreement.

## Categories

| Category | Use for | First action |
| --- | --- | --- |
| BUG | Reproducible behavior that differs from the documented contract | Reproduce against the stated release and add a regression test |
| SECURITY | Suspected vulnerability, credential exposure, or unsafe trust boundary | Stop public discussion and follow the repository [`../SECURITY.md`](../SECURITY.md) private advisory instructions |
| DOCUMENTATION | Incorrect, missing, or unclear public instructions | Verify the command/path and patch the smallest documentation surface |
| FEATURE | A scoped capability request supported by a concrete user problem | Check frozen-contract impact and request evidence in the feature template |
| ENVIRONMENT | OS, capture backend, Docker, TLS, or deployment-specific behavior | Separate environment evidence from code defects and update the matrix if verified |

## Triage rules

1. Confirm the project and agent versions before comparing behavior.
2. Reproduce with the smallest safe fixture or command available.
3. Never request or retain tokens, credentials, private packet payloads, PCAPs,
   or unnecessary customer data.
4. Keep Forecast Score, Candidate Source, and Mitigation Recommendation
   terminology consistent with the public contract.
5. Do not convert an unverified environment into a product regression without
   evidence from that environment.
6. Prefer a narrow defect fix and regression test; do not add speculative
   architecture from a single unsupported request.
