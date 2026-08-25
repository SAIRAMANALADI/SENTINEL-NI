# Final Demo Runbook

## Runtime

Start the Streamlit application:

```powershell
python -m streamlit run app/streamlit_app.py
```

Open the local URL, choose **Full Integrated Demo**, and click **RUN FULL DEMO**.

## 90–120 second demonstration

1. Open the dashboard and select **Full Integrated Demo**.
2. Click **RUN FULL DEMO**.
3. Show the network forecast and the current operating threshold.
4. Show the **Predictive warning** or **No predictive warning** decision.
5. Walk through +10s, +20s, +30s, +40s, and +50s Forecast Scores.
6. Show the candidate-source priorities and their measured activity reasons.
7. Show the mitigation recommendations and the `Simulation only: TRUE` indicator.
8. Open the explanation section and show the existing model sensitivity output.
9. Open Technical Details and show state count, L=10 history, timing, and PCAP attribution status.

## Presenter guardrails

- Do not say attacker detected.
- Do not call Forecast Score a probability; it is not calibrated.
- Do not claim production blocking or automatic mitigation.
- Do not claim CSE-CIC-IDS2018 PCAP attribution is solved.
- Describe the output as an offline replay/prototype demonstration.
- Use **candidate source** and **high-priority source** terminology.

## CLI equivalent

```powershell
python scripts/run_final_demo.py
```

The CLI prints the same five forecast horizons, network status, source priorities, mitigation recommendations, simulation flag, state count, and total processing time.
