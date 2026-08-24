# Attack-Stage Mapping

## Scope and terminology

Dataset labels are observations supplied by a dataset. A **provisional inferred stage** is an internal analytic grouping and is not a ground-truth label. A MITRE ATT&CK technique or tactic is official terminology only when the behavior evidence meets the ATT&CK definition. A dataset label must never be treated as a direct ATT&CK mapping.

No chronological attack chain is asserted in this document. The table records candidate associations that require human review.

| Dataset Attack Label | Observed Behavior | Our Inferred Stage (Provisional) | Potential MITRE Technique/Tactic | Evidence Required | Confidence | Human Verification Required |
| --- | --- | --- | --- | --- | --- | --- |
| CSE-CIC-IDS2018: FTP/SSH brute force | Repeated credential attempts against FTP/SSH services are described by the source | Credential-access attempt | T1110 Brute Force; Credential Access. T1110.001 only if the evidence supports password guessing specifically | Authentication failures, target service, attempt pattern, and any success event | Medium | YES |
| CSE-CIC-IDS2018: Heartbleed | Exploitation of vulnerable OpenSSL/Heartbleed service and memory retrieval are described by the source | Exploitation attempt | Candidate T1190 Exploit Public-Facing Application; Initial Access | Target exposure, exploit traffic, vulnerable service, and post-exploit evidence | Low-Medium | YES |
| CSE-CIC-IDS2018: DoS/DDoS | High-volume or resource-exhaustion traffic against services | Availability-impact attempt | T1498 Network Denial of Service; Impact. T1498.001/`.002` only if direct/reflection behavior is evidenced | Traffic volume, target, protocol, source diversity, and reflection/amplification evidence | Medium | YES |
| CSE-CIC-IDS2018: Web attacks | Source describes scanning and SQL injection, command injection, unrestricted file upload, and XSS activities | Web exploitation activity | Candidate T1190; Initial Access. Do not map every web label to T1190 without evidence | Request/response context, target exposure, exploit payload, and outcome | Low-Medium | YES |
| CSE-CIC-IDS2018: Infiltration | Source describes malicious-file delivery, exploitation, backdoor execution, internal scanning, and exploitation attempts | Multi-behavior sequence candidate; no single stage asserted | Candidate T1190 and T1046 only for supported exploitation/scanning evidence | Event order, internal scan behavior, target services, and post-exploitation evidence | Low | YES |
| CSE-CIC-IDS2018: Bot | Source identifies botnet activity but does not provide an ATT&CK technique label | Malware/C2 candidate; stage UNKNOWN | UNKNOWN until C2 protocol and behavior are evidenced | C2 protocol, beaconing, commands, and host context | Low | YES |
| CTU-13: Botnet | Flow manually labeled as botnet traffic | Botnet-traffic observation; stage UNKNOWN | UNKNOWN; “Botnet” is not an ATT&CK tactic | Scenario documentation, flow context, and malware behavior | Low | YES |
| CTU-13: C&C Channels | Flow manually labeled as C&C channel | Command-and-control candidate; chronology UNKNOWN | Potential application-layer C2 technique only after protocol evidence; official technique ID UNKNOWN here | Protocol, directionality, periodicity, endpoints, and scenario evidence | Low | YES |
| CTU-13: Normal | Flow labeled normal | Benign reference | Not applicable | Dataset labeling documentation | High for dataset label only | NO for ATT&CK mapping |
| CTU-13: Background | Flow labeled background | Unattributed reference traffic | Not applicable; background is not equivalent to benign or malicious | Dataset labeling documentation | High for dataset label only | NO for ATT&CK mapping |

## ATT&CK references consulted

- [T1110 Brute Force](https://attack.mitre.org/techniques/T1110/)
- [T1190 Exploit Public-Facing Application](https://attack.mitre.org/techniques/T1190/)
- [T1498 Network Denial of Service](https://attack.mitre.org/techniques/T1498/)
- [T1046 Network Service Discovery](https://attack.mitre.org/techniques/T1046/)

These references define terminology and evidence expectations; they do not validate a mapping for any dataset row. Mapping sign-off belongs to Developer 4 and must retain the evidence source.
