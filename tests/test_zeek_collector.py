"""Contract tests for the real Zeek conn.log adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.telemetry.collectors.zeek import ZeekCollector


def record(*, ts: float = 1_700_000_000.0, uid: str = "C1") -> dict[str, object]:
    return {
        "ts": ts,
        "uid": uid,
        "id.orig_h": "192.0.2.10",
        "id.resp_h": "198.51.100.20",
        "id.orig_p": 49152,
        "id.resp_p": 443,
        "proto": "tcp",
        "duration": 2.5,
        "orig_bytes": 100,
        "resp_bytes": 200,
        "orig_pkts": 3,
        "resp_pkts": 4,
        "conn_state": "SF",
    }


def write_json_log(path: Path, records: list[dict[str, object]], *, trailing_newline: bool = True) -> None:
    text = "\n".join(json.dumps(item) for item in records)
    if trailing_newline:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def test_valid_json_conn_log_preserves_event_and_arrival_time(tmp_path: Path) -> None:
    path = tmp_path / "conn.log"
    write_json_log(path, [record()])
    collector = ZeekCollector(path, sensor_id="zeek-edge-01")
    collector.start()
    event = collector.read_event()
    assert event is not None
    assert event["timestamp"] == "2023-11-14T22:13:20+00:00"
    assert event["event_timestamp"] == event["timestamp"]
    assert event["arrival_timestamp"] != event["timestamp"]
    assert event["sensor_id"] == "zeek-edge-01"
    assert event["forward_packets"] == 3
    assert collector.status()["source_status"] == "PARTIAL"
    assert collector.status()["source_capabilities"]["state_compatible"] is False


def test_malformed_and_missing_timestamp_records_are_rejected_without_crashing(tmp_path: Path) -> None:
    path = tmp_path / "conn.log"
    path.write_text(
        "not-json\n" + json.dumps({**record(uid="MISSING"), "ts": None}) + "\n" + json.dumps(record(uid="OK")) + "\n",
        encoding="utf-8",
    )
    collector = ZeekCollector(path)
    collector.start()
    event = collector.read_event()
    assert event is not None and event["record_id"] == "OK"
    assert collector.read_event() is None
    assert collector.status()["invalid_count"] == 2


def test_tsv_fields_header_is_supported(tmp_path: Path) -> None:
    path = tmp_path / "conn.log"
    fields = ["ts", "uid", "id.orig_h", "id.resp_h", "id.orig_p", "id.resp_p", "proto", "duration"]
    values = ["1700000001", "T1", "192.0.2.1", "198.51.100.1", "1234", "80", "tcp", "1.0"]
    path.write_text("#fields\t" + "\t".join(fields) + "\n" + "\t".join(values) + "\n", encoding="utf-8")
    collector = ZeekCollector(path)
    collector.start()
    event = collector.read_event()
    assert event is not None
    assert event["destination_port"] == 80
    assert event["flow_duration"] == 1.0


def test_partial_final_line_is_retried_after_append(tmp_path: Path) -> None:
    path = tmp_path / "conn.log"
    path.write_text(json.dumps(record(uid="PARTIAL")), encoding="utf-8")
    collector = ZeekCollector(path)
    collector.start()
    assert collector.read_event() is None
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    event = collector.read_event()
    assert event is not None and event["record_id"] == "PARTIAL"


def test_duplicate_uid_and_late_event_are_reported_separately(tmp_path: Path) -> None:
    path = tmp_path / "conn.log"
    write_json_log(path, [record(ts=1_700_000_010, uid="D"), record(ts=1_700_000_000, uid="L"), record(ts=1_700_000_020, uid="D")])
    collector = ZeekCollector(path)
    collector.start()
    events = collector.read_events(10)
    assert [event["record_id"] for event in events] == ["D", "L"]
    assert collector.read_event() is None
    status = collector.status()
    assert status["duplicate_count"] == 1
    assert status["late_event_count"] == 1


def test_log_rotation_resets_offset(tmp_path: Path) -> None:
    path = tmp_path / "conn.log"
    write_json_log(path, [record(uid="OLD")])
    collector = ZeekCollector(path)
    collector.start()
    assert collector.read_event()["record_id"] == "OLD"
    path.write_text(json.dumps({"ts": 1_700_000_001, "uid": "NEW", "id.orig_h": "192.0.2.1", "id.resp_h": "198.51.100.1", "id.orig_p": 1, "id.resp_p": 2, "proto": "udp"}) + "\n", encoding="utf-8")
    event = collector.read_event()
    assert event is not None and event["record_id"] == "NEW"
    assert collector.status()["rotation_count"] >= 1


def test_allowed_directory_blocks_path_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "conn.log"
    with pytest.raises(ValueError, match="allowed_directory"):
        ZeekCollector(outside, allowed_directory=tmp_path)
