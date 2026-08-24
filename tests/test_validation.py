from __future__ import annotations

from pathlib import Path

from src.features.validation import validate_flow_dataframe
from src.ingestion.cic_ids2018 import load_cic_ids2018_flow


def test_validation_reports_negative_values_and_duplicate_headers(tmp_path: Path) -> None:
    source = tmp_path / "flows.csv"
    source.write_text(
        "Dst Port,Protocol,Timestamp,Flow Duration,Tot Fwd Pkts,TotLen Fwd Pkts,Label\n"
        "443,6,28/02/2018 08:22:13,-1,-2,-3,Benign\n",
        encoding="utf-8",
    )
    frame = load_cic_ids2018_flow(source)
    report = validate_flow_dataframe(frame, frame.attrs["ingestion_stats"])

    assert report["row_count"] == 1
    assert report["duplicate_header_rows"] == 0
    assert report["negative_duration_count"] == 1
    assert report["negative_packet_counts"]["Tot Fwd Pkts"] == 1
    assert report["negative_byte_counts"]["TotLen Fwd Pkts"] == 1
    assert report["labels"]["valid"] is True


def test_validation_reports_clean_timestamp_and_label_state(tmp_path: Path) -> None:
    source = tmp_path / "flows.csv"
    source.write_text(
        "Dst Port,Protocol,Timestamp,Flow Duration,Label\n"
        "443,6,28/02/2018 08:22:13,10,Benign\n"
        "80,6,28/02/2018 08:22:14,20,Infilteration\n",
        encoding="utf-8",
    )
    frame = load_cic_ids2018_flow(source)
    report = validate_flow_dataframe(frame, frame.attrs["ingestion_stats"])

    assert report["timestamp"]["missing_or_invalid_count"] == 0
    assert report["timestamp"]["chronologically_ordered"] is True
    assert report["duplicate_rows"] == 0
    assert report["labels"]["counts"] == {"Benign": 1, "Infilteration": 1}
