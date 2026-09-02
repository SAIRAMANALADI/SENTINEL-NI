"""Deterministic public-release hygiene audit with no third-party dependencies."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile
import tarfile


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "requirements.lock.txt",
    "docs/OPERATOR_QUICKSTART.md",
    "docs/ENVIRONMENT_SUPPORT.md",
    "docs/RELEASE_MANIFEST.md",
    "docs/DEVELOPMENT.md",
    "docs/RELEASE_NOTES.md",
)
PROTECTED_PREFIXES = (
    "src/models/",
    "src/forecasting/",
    "src/features/",
    "src/ingestion/",
    "data/raw/",
    "data/processed/",
)
PROTECTED_FILES = {"configs/state_feature_schema.yaml", "docs/TARGET_STATE_SPEC.md", "docs/DATA_CONTRACT.md"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PRIVATE) KEY-----"),
    re.compile(r"\b(?:ghp_|github_pat_|xox[baprs]-|sk-[A-Za-z0-9])\S+"),
    re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+(?!<|token\b|example\b|redacted\b)[A-Za-z0-9._-]{20,}"),
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"(?i)[A-Z]:\\Users\\[^\\/\s]+\\"),
    re.compile(r"/home/(?!app(?:/|$)|<)[^/\s]+/"),
    re.compile(r"/Users/(?!<)[^/\s]+/"),
)
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
    return result.stdout


def tracked_files() -> list[Path]:
    names = _git("ls-files", "-z").split("\0")
    return [ROOT / name for name in names if name]


def text_files() -> list[Path]:
    allowed = {".md", ".txt", ".toml", ".yaml", ".yml", ".py", ".json", ".ts", ".tsx", ".js", ".jsx"}
    paths = set(tracked_files())
    for base in (ROOT / "docs", ROOT / "scripts", ROOT / ".github", ROOT / "frontend"):
        if not base.exists():
            continue
        paths.update(path for path in base.rglob("*") if path.is_file() and path.suffix.lower() in allowed and "node_modules" not in path.parts)
    return sorted(paths)


def protected_changes() -> list[str]:
    names = set()
    for args in (("diff", "--name-only"), ("diff", "--cached", "--name-only")):
        names.update(line.strip().replace("\\", "/") for line in _git(*args).splitlines() if line.strip())
    return sorted(name for name in names if name in PROTECTED_FILES or any(name.startswith(prefix) for prefix in PROTECTED_PREFIXES))


def unsafe_untracked() -> list[str]:
    names: list[str] = []
    for line in _git("status", "--porcelain=v1").splitlines():
        if not line.startswith("?? "):
            continue
        name = line[3:].strip().strip('"').replace("\\", "/")
        lower = name.lower()
        if any(token in lower for token in (".env", ".pem", ".key", ".p12", ".pcap", ".parquet", "__pycache__", ".pytest_cache", "node_modules", "graphify-out")) or lower.endswith((".log", ".tmp")):
            names.append(name)
    return names


def ignored_runtime_artifacts() -> list[str]:
    names: set[str] = set()
    for line in _git("status", "--short", "--ignored", "--untracked-files=all").splitlines():
        if not line.startswith("!! "):
            continue
        name = line[3:].strip().strip('"').replace("\\", "/")
        lower = name.lower()
        if not any(token in lower for token in (".venv", ".pytest_cache", "__pycache__", "node_modules", ".next", "graphify-out", "data/raw", "data/processed", "models/", "results/", "dist/", "build/", ".parquet", ".pcap", ".csv")):
            continue
        parts = name.rstrip("/").split("/")
        if "__pycache__" in parts:
            names.add(parts[0] + "/**/__pycache__/")
        elif parts[0] in {".venv", ".pytest_cache", "build", "dist", "graphify-out"}:
            names.add(parts[0] + "/")
        elif parts[0] in {"app", "data", "frontend", "models", "results"}:
            names.add(parts[0] + "/")
        else:
            names.add(name)
    return sorted(names)


def scan_patterns(paths: list[Path], patterns: tuple[re.Pattern[str], ...]) -> list[str]:
    hits: list[str] = []
    for path in paths:
        if path == Path(__file__).resolve() or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(content.splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    return hits


def broken_links() -> list[str]:
    broken: list[str] = []
    for path in text_files():
        if path.suffix.lower() != ".md":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for raw_target in LINK_PATTERN.findall(content):
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            candidate = (path.parent / target).resolve()
            if not candidate.exists():
                broken.append(f"{path.relative_to(ROOT).as_posix()} -> {target}")
    return broken


def package_artifact_issues() -> list[str]:
    issues: list[str] = []
    artifacts = sorted((ROOT / "dist").glob("*.whl")) + sorted((ROOT / "dist").glob("*.tar.gz"))
    for artifact in artifacts:
        try:
            if artifact.suffix == ".whl":
                with ZipFile(artifact) as archive:
                    names = archive.namelist()
            else:
                with tarfile.open(artifact) as archive:
                    names = archive.getnames()
        except (OSError, tarfile.TarError):
            issues.append(f"unreadable package artifact: {artifact.name}")
            continue
        for name in names:
            lower = name.lower()
            if any(token in lower for token in (".env", ".pem", ".key", ".p12", "data/raw", "data/processed", ".pcap", ".parquet")):
                issues.append(f"forbidden package member: {artifact.name}:{name}")
    return issues


def run(strict: bool = False) -> int:
    failures: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            failures.append(f"missing required release file: {relative}")
    failures.extend(f"obvious secret pattern: {hit}" for hit in scan_patterns(text_files(), SECRET_PATTERNS))
    failures.extend(f"developer-local path: {hit}" for hit in scan_patterns(text_files(), LOCAL_PATH_PATTERNS))
    failures.extend(f"broken documentation link: {item}" for item in broken_links())
    failures.extend(f"protected path changed: {item}" for item in protected_changes())
    failures.extend(package_artifact_issues())
    unsafe = unsafe_untracked()
    if unsafe:
        message = "untracked runtime/sensitive artifacts: " + ", ".join(unsafe)
        (failures if strict else warnings).append(message)
    ignored = ignored_runtime_artifacts()
    if ignored:
        preview = ", ".join(ignored[:12])
        suffix = " …" if len(ignored) > 12 else ""
        warnings.append(f"ignored local artifacts are present but not commit candidates ({len(ignored)}): {preview}{suffix}")
    print(f"Release audit root: {ROOT}")
    print(f"Tracked text files scanned: {len(text_files())}")
    print(f"Required release files: {len(REQUIRED_FILES)}")
    print(f"Package artifacts inspected: {len(list((ROOT / 'dist').glob('*.whl'))) + len(list((ROOT / 'dist').glob('*.tar.gz')))}")
    for warning in warnings:
        print(f"WARN {warning}")
    for failure in failures:
        print(f"FAIL {failure}")
    print("RELEASE_AUDIT=PASS" if not failures else f"RELEASE_AUDIT=FAIL ({len(failures)} issue(s))")
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="fail on unsafe untracked runtime artifacts")
    return run(strict=parser.parse_args().strict)


if __name__ == "__main__":
    raise SystemExit(main())
