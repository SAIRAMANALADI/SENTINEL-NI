"""Generate deterministic DEMO / TEST DATA for the integrated offline demo."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "samples" / "final_demo_events.csv"
STATUS = "DEMO / TEST DATA - NOT RESEARCH DATA"


def _row(timestamp: str, source_index: int, offset: int, packet_length: int, destination_index: int, destination_port: int) -> dict[str, object]:
    source_ip = f"10.0.0.{source_index}"
    destination_ip = f"10.0.0.{10 + destination_index}"
    flow_duration = 1000 + (source_index * 10) + offset
    return {
        "timestamp": timestamp,
        "capture_date": "2018-02-22",
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "source_port": 40000 + source_index * 100 + offset,
        "destination_port": destination_port,
        "protocol": "TCP",
        "packet_length": packet_length,
        "tcp_flags": "SYN,ACK" if offset == 0 else "ACK",
        "Label": "Benign",
        "Dst Port": destination_port,
        "Flow Duration": flow_duration,
        "Tot Fwd Pkts": 2,
        "Tot Bwd Pkts": 1,
        "TotLen Fwd Pkts": packet_length,
        "TotLen Bwd Pkts": packet_length // 2,
        "Flow IAT Mean": 10.0,
        "Flow IAT Std": 2.0,
        "SYN Flag Cnt": 1 if offset == 0 else 0,
        "ACK Flag Cnt": 1,
        "RST Flag Cnt": 0,
        "Pkt Len Mean": float(packet_length),
        "Pkt Len Std": 1.0,
        "demo_status": STATUS,
    }


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    base = "2018-02-22T01:{:02d}:{:02d}"
    for interval in range(10):
        minute = interval // 6
        second = (interval * 10) % 60
        # Source A: one stable flow per interval.
        rows.append(_row(base.format(minute, second), 1, 0, 100, 10, 443))

        # Source B: one additional flow per interval and increasing packet size.
        for offset in range(interval + 1):
            rows.append(_row(base.format(minute, second + (offset % 8)), 2, offset, 150 + interval * 80, 20 + (offset % 3), [443, 80, 22][offset % 3]))

        # Source C: stable single flow, then a large final-interval burst.
        burst_size = 12 if interval == 9 else 1
        for offset in range(burst_size):
            rows.append(_row(base.format(minute, second + (offset % 8)), 3, offset, 1000 if interval == 9 else 180, 30 + (offset % 5), [443, 22, 80, 8080, 8443][offset % 5]))
    return rows


def main() -> None:
    rows = build_rows()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        handle.write("# DEMO / TEST DATA - NOT RESEARCH DATA\n")
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} deterministic demo events to {OUTPUT}")


if __name__ == "__main__":
    main()
