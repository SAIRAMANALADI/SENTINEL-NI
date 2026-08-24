from __future__ import annotations

from pathlib import Path

import pandas as pd


DATASET = Path("data/processed/cic_ids2018_network_states.parquet")
TRAIN_DAYS = {"2018-02-14", "2018-02-21"}
VALIDATION_DAYS = {"2018-02-22"}
FINAL_TEST_DAYS = {"2018-02-28"}
EXPECTED_DAYS = TRAIN_DAYS | VALIDATION_DAYS | FINAL_TEST_DAYS


def _available_days() -> set[str]:
    frame = pd.read_parquet(DATASET, columns=["capture_day"])
    return set(frame["capture_day"].astype(str).unique())


def test_all_available_days_are_known_and_assigned() -> None:
    assert _available_days() == EXPECTED_DAYS


def test_no_unseen_development_day_is_selected_from_frozen_roles() -> None:
    available = _available_days()
    eligible = available - TRAIN_DAYS - VALIDATION_DAYS - FINAL_TEST_DAYS
    assert eligible == set()


def test_generalization_day_cannot_overlap_train_validation_or_final_test() -> None:
    available = _available_days()
    roles = [TRAIN_DAYS, VALIDATION_DAYS, FINAL_TEST_DAYS]
    assert sum(len(role) for role in roles) == len(set().union(*roles))
    assert available == set().union(*roles)


def test_final_test_day_is_reserved_and_not_a_generalization_fallback() -> None:
    available = _available_days()
    eligible_without_test = available - TRAIN_DAYS - VALIDATION_DAYS - FINAL_TEST_DAYS
    assert "2018-02-28" not in eligible_without_test
    assert FINAL_TEST_DAYS == {"2018-02-28"}
