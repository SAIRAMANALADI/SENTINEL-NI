# Offline Demo Runbook

## Current status

The dashboard and inference pipeline do not exist yet. This runbook defines the intended foundation-to-demo handoff without fabricating outputs.

## Target workflow

1. Install the pinned or approved project dependencies.
2. Select the approved small sample or deterministic fixture.
3. Validate the input against the canonical data contract.
4. Load saved preprocessing and model artifacts.
5. Run inference without training or network access.
6. Display current state, K-step forecast, stage evidence, explanation, and baseline comparison.
7. Record the command, artifact versions, and environment.

## Acceptance criteria for the future demo

- A clean machine can follow the README setup.
- No large dataset download is required during inference.
- No metrics or model output are hard-coded as if measured.
- Missing or unsupported input produces a clear validation error.
- The CLI fallback remains usable if the dashboard is unavailable.
- The run is deterministic under the configured seed where the framework permits it.

## Required evidence before sign-off

- Clean-environment command output.
- Model and preprocessing artifact identifiers.
- Sample input provenance.
- Reproducible results file.
- Known limitations and uncertainty notes.
