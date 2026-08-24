from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from scripts.prepare_cic_flow import select_model_features
from src.ingestion.cic_ids2018 import load_cic_ids2018_flow


CSV = """Dst Port,Protocol,Timestamp,Flow Duration,Tot Fwd Pkts,Tot Bwd Pkts,TotLen Fwd Pkts,TotLen Bwd Pkts,Flow Byts/s,Flow Pkts/s,Label
443,6,28/02/2018 08:22:13,0,2,0,0,0,NaN,Infinity,Benign
Dst Port,Protocol,Timestamp,Flow Duration,Tot Fwd Pkts,Tot Bwd Pkts,TotLen Fwd Pkts,TotLen Bwd Pkts,Flow Byts/s,Flow Pkts/s,Label
80,6,28/02/2018 08:22:14,1000,1,1,40,80,120000,2000,Infilteration
"""


def test_repeated_header_is_removed_and_legitimate_rows_preserved(tmp_path: Path) -> None:
    source = tmp_path / "flows.csv"
    source.write_text(CSV, encoding="utf-8")
    before = hashlib.sha256(source.read_bytes()).hexdigest()

    frame = load_cic_ids2018_flow(source, chunksize=2)

    assert len(frame) == 2
    assert frame["source_row_number"].tolist() == [1, 3]
    assert frame["Label"].tolist() == ["Benign", "Infilteration"]
    assert frame["original_label"].tolist() == ["Benign", "Infilteration"]
    assert frame["binary_label"].tolist() == [0, 1]
    assert frame["Flow Byts/s"].isna().tolist() == [True, False]
    assert frame["Flow Byts/s__raw"].tolist() == ["NaN", "120000"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_model_feature_selection_has_no_nonfinite_values(tmp_path: Path) -> None:
    source = tmp_path / "flows.csv"
    source.write_text(CSV, encoding="utf-8")
    frame = load_cic_ids2018_flow(source)
    exclusions = {
        "Label": {},
        "original_label": {},
        "binary_label": {},
        "Timestamp": {},
        "timestamp_parsed": {},
        "Dst Port": {},
        "Protocol": {},
        "Flow Byts/s": {},
        "Flow Pkts/s": {},
        "Flow Byts/s__raw": {},
        "Flow Pkts/s__raw": {},
        "source_row_number": {},
    }
    columns = select_model_features(frame, exclusions)
    values = frame[columns].select_dtypes(include=[np.number]).to_numpy(dtype="float64")
    assert columns == ["Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts", "TotLen Fwd Pkts", "TotLen Bwd Pkts"]
    assert np.isfinite(values).all()
    assert not frame[columns].isna().any().any()
