from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.build_state_splits import build_splits
from src.features.network_state import FEATURE_COLUMNS, METADATA_COLUMNS, TARGET_COLUMNS


def test_state_split_is_complete_day_and_isolated(tmp_path: Path) -> None:
    rows = []
    for day, role in [("2018-02-14", "train"), ("2018-02-22", "validation"), ("2018-02-28", "test")]:
        for index in range(2):
            row = {column: 0.0 for column in FEATURE_COLUMNS}
            row.update(
                {
                    "timestamp": pd.Timestamp(day) + pd.Timedelta(seconds=index * 10),
                    "capture_day": day,
                    "malicious_flow_count": index,
                    "malicious_flow_ratio": float(index),
                    "binary_attack_state": index,
                    "future_attack_state": index if index == 0 else -1,
                    "future_target_available": index == 0,
                }
            )
            rows.append(row)
    frame = pd.DataFrame(rows, columns=METADATA_COLUMNS + FEATURE_COLUMNS + TARGET_COLUMNS)
    input_path = tmp_path / "states.parquet"
    frame.to_parquet(input_path, index=False)
    split_path = tmp_path / "split.json"
    split_path.write_text(
        json.dumps(
            {
                "train_days": ["2018-02-14"],
                "validation_days": ["2018-02-22"],
                "test_days": ["2018-02-28"],
            }
        ),
        encoding="utf-8",
    )
    report = build_splits(input_path, split_path, tmp_path / "out", tmp_path / "report.json")
    assert report["split_day_overlap"] is False
    assert report["cross_day_aggregation"] is False
    assert set(pd.read_parquet(tmp_path / "out" / "train.parquet")["capture_day"]) == {"2018-02-14"}
    assert set(pd.read_parquet(tmp_path / "out" / "validation.parquet")["capture_day"]) == {"2018-02-22"}
    assert set(pd.read_parquet(tmp_path / "out" / "test.parquet")["capture_day"]) == {"2018-02-28"}
