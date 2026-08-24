"""Check the local environment and lightweight offline demo artifacts."""

from __future__ import annotations

import importlib.util
import importlib.metadata
import platform
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PACKAGES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "scikit-learn": "sklearn",
    "joblib": "joblib",
    "PyYAML": "yaml",
    "torch": "torch",
    "streamlit": "streamlit",
    "pytest": "pytest",
}
REQUIRED_DIRECTORIES = ["app", "configs", "data/samples", "models", "src", "tests"]
REQUIRED_FILES = [
    "models/logistic_baseline.joblib",
    "models/baseline_preprocessor.joblib",
    "models/lstm_multistep_k5.pt",
    "configs/operating_policy.yaml",
    "configs/state_feature_schema.yaml",
    "data/samples/inference_demo_sequence.csv",
]


def _check(label: str, passed: bool, detail: str) -> tuple[bool, str]:
    status = "PASS" if passed else "FAIL"
    return passed, f"{status:<4} {label}: {detail}"


def run_checks() -> tuple[bool, list[str]]:
    checks: list[tuple[bool, str]] = []
    checks.append(_check("Python version", sys.version_info >= (3, 10), sys.version.split()[0]))
    checks.append(_check("Operating system", True, platform.platform()))
    for distribution, module in REQUIRED_PACKAGES.items():
        present = importlib.util.find_spec(module) is not None
        try:
            version = importlib.metadata.version(distribution) if present else "not installed"
        except importlib.metadata.PackageNotFoundError:
            version = "version unavailable"
        checks.append(_check(f"Package {distribution}", present, version))
    for relative in REQUIRED_DIRECTORIES:
        path = PROJECT_ROOT / relative
        checks.append(_check(f"Directory {relative}", path.is_dir(), str(path)))
    for relative in REQUIRED_FILES:
        path = PROJECT_ROOT / relative
        checks.append(_check(f"Artifact {relative}", path.is_file() and path.stat().st_size > 0, str(path)))
    passed = all(result for result, _line in checks)
    return passed, [line for _result, line in checks]


def main() -> int:
    passed, lines = run_checks()
    print(f"Environment check: {'PASS' if passed else 'FAIL'}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Python: {sys.version.split()[0]} | OS: {platform.platform()}")
    print("\n".join(lines))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
