# Dependency Audit

## Direct runtime dependencies

| Package | Why it is present | Requirement |
|---|---|---|
| numpy | Numeric arrays and finite-value checks | `numpy>=2.0,<3` |
| pandas | State sequence input and display tables | `pandas>=2.2,<4` |
| pyarrow | Parquet input support | `pyarrow>=18.0,<23` |
| scikit-learn | Frozen preprocessing/metrics artifacts | `scikit-learn>=1.5,<2` |
| joblib | Preprocessing/model artifact loading | `joblib>=1.4,<2` |
| torch | Frozen LSTM checkpoint inference | `torch>=2.0,<3` |
| PyYAML | Feature schema and policy loading | `PyYAML>=6.0,<7` |
| streamlit | Offline dashboard runtime | `streamlit>=1.37,<2` |

## Development/test dependency

`pytest>=8.0,<10` runs the repository test suite and is included in the lightweight setup requirements.

## Findings

- The prior requirements file omitted explicit NumPy, PyTorch, and joblib entries even though the inference path imports/uses them directly. Those entries were added for clean-environment reproducibility.
- The dashboard uses Streamlit built-in charting; Plotly and other visualization packages are not required.
- No AWS SDK, OpenAI client, cloud SDK, or external API client is required by the offline prototype.
- Version ranges are bounded at major-version level; the acceptance environment records its installed versions in `scripts/check_environment.py` output.
