# Offline Demo Runbook

## Current status

The offline inference API, CLI, and Streamlit dashboard are implemented and consume the frozen local K=5 development checkpoint. This runbook describes the verified demo path; it does not train models or download data.

## Target workflow

1. Install the pinned or approved project dependencies.
2. Select the approved small sample or deterministic fixture.
3. Validate the input against the canonical data contract.
4. Load saved preprocessing and model artifacts.
5. Run inference without training or network access.
6. Display current state, K-step forecast, stage evidence, explanation, and baseline comparison.
7. Record the command, artifact versions, and environment.

## Acceptance criteria for the demo

- A clean machine can follow the README setup.
- No large dataset download is required during inference.
- No metrics or model output are hard-coded as if measured; the dashboard displays `Verified locally` instead of a stale test count.
- Missing or unsupported input produces a clear validation error.
- The CLI fallback remains usable if the dashboard is unavailable.
- The run is deterministic under the configured seed where the framework permits it.

## Verified local command

```powershell
python run.py `
  --input data/samples/inference_demo_sequence.csv `
  --output results/e2e_cli_result.json
```

The CLI returns five Forecast Score rows at +10s through +50s, applies the configured Balanced policy, and writes JSON. The Streamlit path is:

```powershell
python -m streamlit run app/streamlit_app.py --server.headless true
```

Use **Run Demo** with `data/samples/inference_demo_sequence.csv`. The API performs the authoritative 10-row, 17-feature, timestamp, and capture-day validation.

## Evidence to record for a release

- Clean-environment command output.
- Model and preprocessing artifact identifiers.
- Sample input provenance.
- Reproducible results file.
- Known limitations and uncertainty notes.
