"""Foundation-only smoke test.

This script intentionally does not require a dataset, trained model, or
network access. It checks only the project runtime foundation.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "project.yaml"

REQUIRED_DIRECTORIES = (
    "data/raw",
    "data/processed",
    "data/samples",
    "src/ingestion",
    "src/features",
    "src/preprocessing",
    "src/models",
    "src/forecasting",
    "src/mitre",
    "src/explainability",
    "app",
    "configs",
    "tests",
    "notebooks",
    "models",
    "results",
    "docs",
    "scripts",
)

REQUIRED_CONFIG_KEYS = (
    "project",
    "paths",
    "runtime",
)

IMPORTS = (
    "src",
    "src.ingestion",
    "src.features",
    "src.preprocessing",
    "src.models",
    "src.forecasting",
    "src.mitre",
    "src.explainability",
    "app",
)


def main() -> int:
    print(f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required for the foundation.")

    missing_directories = [
        path for path in REQUIRED_DIRECTORIES if not (PROJECT_ROOT / path).is_dir()
    ]
    if missing_directories:
        raise RuntimeError(f"Missing required directories: {missing_directories}")

    if not CONFIG_PATH.is_file():
        raise RuntimeError(f"Missing configuration: {CONFIG_PATH}")
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or any(key not in config for key in REQUIRED_CONFIG_KEYS):
        raise RuntimeError("Configuration is missing one or more top-level sections.")

    sys.path.insert(0, str(PROJECT_ROOT))
    for module_name in IMPORTS:
        importlib.import_module(module_name)

    print(f"Configuration loaded: {CONFIG_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Imported {len(IMPORTS)} foundation packages")
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
