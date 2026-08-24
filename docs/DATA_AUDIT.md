# Data Audit

## Current status

The local repository contains no CSV, PCAP, PCAPNG, Parquet, archive, or PDF dataset artifact. No dataset was downloaded during reconnaissance. The official SIH problem statement is also absent.

Candidate reconnaissance is documented in [DATASET_SELECTION.md](DATASET_SELECTION.md). The current recommendation is provisional because it cannot yet be checked against the official PS.

## Required audit record before processing

| Item | Evidence required | Status |
| --- | --- | --- |
| Dataset name and official source | URL, release, and citation | Candidate sources recorded; final selection pending |
| License and access | License text and access conditions | Candidate-level evidence recorded; verify before use |
| Selected subset | Scenario/file names and selection rule | Pending |
| Traffic granularity | Flow, packet, or both | Candidate-level evidence recorded; sample inspection pending |
| Timestamp coverage | Range, timezone, and ordering | Exact selected-file fields pending |
| Attack types and labels | Label dictionary and ground-truth source | Candidate-level evidence recorded; final label contract pending |
| Missing and invalid values | Profiling output and decisions | Pending |
| Duplicates | Detection rule and counts | Pending |
| Feature provenance | Raw-to-canonical mapping | Pending |
| Privacy handling | IP and payload handling decision | Pending |
| Official PS alignment | Direct requirement-to-data evidence | Blocked: OFFICIAL PS TEXT REQUIRED |

Do not download or commit a large dataset as part of reconnaissance. Use the placeholder scripts only with an explicit local source path.
