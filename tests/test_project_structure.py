from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

REQUIRED_FILES = (
    "README.md",
    "requirements.txt",
    ".gitignore",
    "configs/project.yaml",
    "docs/PS_REQUIREMENT_MATRIX.md",
    "docs/ARCHITECTURE.md",
    "docs/DATA_CONTRACT.md",
    "docs/DATA_AUDIT.md",
    "docs/DECISIONS.md",
    "docs/LEAKAGE_AUDIT.md",
    "docs/DEMO_RUNBOOK.md",
    "docs/DATASET_SELECTION.md",
    "docs/DATA_REQUIREMENT_MATRIX.md",
    "docs/ATTACK_STAGE_MAPPING.md",
    "docs/TEMPORAL_FORECASTING_SPEC.md",
    "docs/REQUIREMENTS_AND_DATA_READINESS.md",
    "docs/RAW_DATA_PROFILE.md",
    "docs/FEATURE_LEAKAGE_REPORT.md",
    "results/data_pipeline_report.md",
    "scripts/smoke_test.py",
    "scripts/download_dataset.py",
    "scripts/prepare_dataset.py",
)

PACKAGE_INIT_FILES = (
    "src/__init__.py",
    "src/ingestion/__init__.py",
    "src/features/__init__.py",
    "src/preprocessing/__init__.py",
    "src/models/__init__.py",
    "src/forecasting/__init__.py",
    "src/mitre/__init__.py",
    "src/explainability/__init__.py",
    "app/__init__.py",
    "scripts/__init__.py",
)


def test_required_directories_exist() -> None:
    missing = [path for path in REQUIRED_DIRECTORIES if not (PROJECT_ROOT / path).is_dir()]
    assert not missing, f"Missing required directories: {missing}"


def test_required_files_exist() -> None:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    assert not missing, f"Missing required files: {missing}"


def test_package_placeholders_exist() -> None:
    missing = [path for path in PACKAGE_INIT_FILES if not (PROJECT_ROOT / path).is_file()]
    assert not missing, f"Missing package placeholders: {missing}"
