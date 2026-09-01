# Current Limitations

- The runtime is single-node and process-local; it is not highly available or
  horizontally coordinated.
- Live capture is host-dependent and requires an explicitly visible interface
  plus Npcap/libpcap and permissions.
- The packet-to-flow path is implemented for the current metadata contract;
  no arbitrary packet source is supported automatically.
- Source prioritization is evidence-based review ranking, not attacker
  attribution.
- Mitigation is simulation-only; no automatic blocking is implemented.
- PCAP fusion with the frozen CSE-CIC-IDS2018 flow export remains unsupported
  without authoritative matching provenance.
- Authentication is bearer-token RBAC, not OIDC/OAuth2 identity management.
- Audit storage, metrics, and runtime state are local to the process.
- No measured production capacity, soak, chaos, HA, or penetration-test claim
  is made by the current repository.
- The MIT license covers project-owned code. Dataset, PCAP, and model
  redistribution terms remain separate and require release-owner review.
