from __future__ import annotations

import pandas as pd

from src.features.timestamps import parse_timestamp_column, timestamp_audit


def test_timestamp_format_is_parsed_without_timezone_conversion() -> None:
    frame = parse_timestamp_column(
        pd.DataFrame({"Timestamp": ["28/02/2018 08:22:13", "28/02/2018 08:22:14"]})
    )
    audit = timestamp_audit(frame)

    assert str(frame["timestamp_parsed"].iloc[0]) == "2018-02-28 08:22:13"
    assert audit["missing_or_invalid_count"] == 0
    assert audit["chronologically_ordered"] is True
    assert "no timezone conversion" in audit["timezone_assumption"]


def test_invalid_timestamp_is_reported() -> None:
    frame = parse_timestamp_column(
        pd.DataFrame({"Timestamp": ["28/02/2018 08:22:13", "not-a-timestamp"]})
    )
    audit = timestamp_audit(frame)

    assert audit["missing_or_invalid_count"] == 1
