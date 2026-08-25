# Final Demo Architecture

## Demonstration scope

The final integrated demonstration is an **offline replay demonstration** using `data/samples/final_demo_events.csv`. The file is synthetic test data and is explicitly marked `DEMO / TEST DATA - NOT RESEARCH DATA`.

## Data flow

```text
final_demo_events.csv
        |
        +--> existing source-event validation and 10-second source activity
        |
        +--> existing frozen flow-window aggregation
                    |
                    v
             10-second network state
                    |
                    v
             StateBuffer, L=10
                    |
                    v
       existing LSTM K=5 inference API
                    |
                    v
          Forecast Score + policy decision
                    |
                    +--> existing explanation output
                    |
                    +--> existing source prioritization
                                  |
                                  v
                         mitigation recommendation
```

The orchestration layer is `src/streaming/final_demo_engine.py`. It composes existing modules and does not contain model mathematics, scaling, target logic, or a second policy.

## User-visible result

The Streamlit `Full Integrated Demo` mode is started with the **RUN FULL DEMO** button and shows:

- five actual K=5 Forecast Scores at +10/+20/+30/+40/+50 seconds;
- the existing balanced operating threshold and Predictive warning/No predictive warning;
- candidate-source priority and measured reasons;
- recommendation-only mitigation with `Simulation only: TRUE`;
- the existing explainability output;
- timing and PCAP-attribution status in technical details.

## Integrity boundaries

- The frozen 17 features, 10-second interval, L=10 history, K=5 checkpoint, target, operating policy, and scientific artifacts are unchanged.
- Forecast values are produced by `predict_network_state_sequence`; no score is fabricated.
- Source rows use `candidate source` terminology and never claim attacker identity.
- No real traffic, firewall, WAF, or API gateway is modified.
- CSE-CIC-IDS2018 PCAP attribution remains unverified and is not used by this demo.
