# Initial Architecture

## Scope

This is the initial engineering architecture for an offline network-attack-forecasting prototype. It is deliberately model-agnostic beyond the provisional baseline and first temporal-model decision. Dataset-specific details and official SIH requirements remain to be verified.

## Logical flow

```text
Traffic Input
    ↓
Ingestion
    ↓
Feature Extraction
    ↓
Canonical Feature Schema
    ↓
Temporal Window Construction
    ↓
Baseline Model
    ↓
Temporal World Model
    ↓
K-Step Forecasting
    ↓
Attack Stage Mapping
    ↓
Explainability
    ↓
Offline Dashboard
```

## Training path

```text
Approved dataset
  → ingestion and validation
  → canonical feature table
  → time/scenario-aware split
  → deterministic preprocessing artifact
  → temporal window construction
  → baseline training and evaluation
  → first temporal-model training and evaluation
  → saved model and preprocessing artifacts
  → results and audit reports
```

Training must not be performed by the dashboard. Splits, feature transformations, labels, and metrics must be reproducible and recorded.

## Inference path

```text
CSV or approved traffic input
  → ingestion and validation
  → canonical feature table
  → load preprocessing and model artifacts
  → construct latest temporal window
  → baseline and temporal inference
  → K-step forecast
  → attack-stage mapping with evidence
  → explainability output with caveats
  → offline dashboard or CLI result
```

The inference path must not silently retrain, download data, or depend on an external service.

## Module boundaries

| Boundary | Responsibility | Contract |
| --- | --- | --- |
| `src/ingestion/` → `src/features/` | Parse and normalize traffic | Validated raw records |
| `src/features/` → `src/preprocessing/` | Produce canonical rows and labels | `docs/DATA_CONTRACT.md` |
| `src/preprocessing/` → `src/models/` | Produce deterministic training inputs | Versioned preprocessing configuration |
| `src/models/` → `src/forecasting/` | Provide saved model inference | Structured model output |
| `src/forecasting/` → `app/` | Provide user-facing forecast data | Inference result interface |
