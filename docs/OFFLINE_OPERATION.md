# Offline Operation Audit

## Result

The prototype is designed to run offline after its Python dependencies are installed.

Runtime execution uses:

- `src/forecasting/inference.py`;
- local model checkpoints and preprocessing artifact under `models/`;
- local policy/schema files under `configs/`;
- the local demo fixture under `data/samples/`.

The Streamlit app and CLI do not call AWS, OpenAI, external APIs, cloud services, or network URLs. No API key or internet connection is required during inference or dashboard execution.

## Dependency boundary

Package installation may require access to the configured Python package index in a clean environment. Once the packages are installed, the actual demo path is local-only. An offline deployment should provision the wheel cache or environment ahead of time.

## Audit evidence

- The dashboard imports Streamlit, pandas, and the local inference module only.
- The CLI reads the supplied local input and writes local JSON.
- No runtime code in the demo path contains AWS, OpenAI, HTTP, or cloud-service calls.
- The final test day and raw datasets are not required by the demo.
