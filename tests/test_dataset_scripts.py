from pathlib import Path

import pytest

from scripts.download_dataset import (
    prepare_raw_directory,
    validate_expected_paths,
    validate_source,
)
from scripts.prepare_dataset import (
    prepare_processed_directory,
    read_csv_header,
    validate_expected_columns,
    validate_input,
)


def test_download_helpers_validate_local_source_and_expected_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    expected = source / "flows.csv"
    expected.write_text("timestamp,label\n", encoding="utf-8")

    assert validate_source(source) == source.resolve()
    assert validate_expected_paths(source, ["flows.csv"]) == [expected]
    assert prepare_raw_directory(tmp_path / "raw").is_dir()


def test_download_helpers_fail_for_missing_expected_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(FileNotFoundError, match="Required dataset paths"):
        validate_expected_paths(source, ["missing.csv"])


def test_prepare_helpers_validate_csv_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "flows.csv"
    csv_path.write_text("timestamp,label\n2026-01-01T00:00:00Z,normal\n", encoding="utf-8")

    assert validate_input(csv_path) == csv_path.resolve()
    header = read_csv_header(csv_path)
    validate_expected_columns(header, ["timestamp", "label"])
    assert prepare_processed_directory(tmp_path / "processed").is_dir()


def test_prepare_helpers_fail_for_missing_csv_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "flows.csv"
    csv_path.write_text("timestamp,label\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Required CSV columns"):
        validate_expected_columns(read_csv_header(csv_path), ["src_ip"])


def test_prepare_helpers_fail_for_missing_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Dataset input does not exist"):
        validate_input(tmp_path / "missing.csv")
