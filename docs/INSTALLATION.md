# Installation and Offline Demo Setup

These steps are intended for a clean clone. They use a project-local virtual environment and do not rely on globally installed packages.

## Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_environment.py
python run.py --input data/samples/inference_demo_sequence.csv --output results/e2e_cli_result.json
streamlit run app/streamlit_app.py
```

## macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_environment.py
python run.py --input data/samples/inference_demo_sequence.csv --output results/e2e_cli_result.json
streamlit run app/streamlit_app.py
```

The dashboard uses only local model, preprocessing, configuration, and sample files. Raw and processed research datasets are not required for the demo.
