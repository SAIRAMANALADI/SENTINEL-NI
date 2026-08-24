from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.cic_ids2018 import load_cic_ids2018_flow


def test_multiday_ingestion_preserves_arbitrary_source_labels(tmp_path: Path) -> None:
    csv = tmp_path / "Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv"
    csv.write_text(
        "Dst Port,Protocol,Timestamp,Flow Duration,Label\n"
        "21,6,14/02/2018 10:32:00,100,FTP-BruteForce\n"
        "22,6,14/02/2018 10:33:00,200,Benign\n",
        encoding="utf-8",
    )

    frame = load_cic_ids2018_flow(csv, preserve_source_labels=True)

    assert frame["Label"].tolist() == ["FTP-BruteForce", "Benign"]
    assert frame["original_label"].tolist() == ["FTP-BruteForce", "Benign"]
    assert "binary_label" not in frame.columns
    assert pd.api.types.is_datetime64_dtype(frame["timestamp_parsed"])
