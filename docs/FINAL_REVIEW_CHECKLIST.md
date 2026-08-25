# Final Review Checklist

Evidence-backed status from the 2026-08-25 acceptance pass:

- [x] backend starts
- [x] dashboard starts
- [x] health passes
- [x] readiness passes
- [x] live capture starts on the host Wi-Fi interface
- [x] real packets observed
- [x] real flows observed
- [x] live states observed
- [x] 10-state history reached
- [x] real LSTM forecast reached
- [x] rolling forecast verified
- [x] source priorities shown
- [x] mitigation shown
- [x] simulation-only label shown
- [x] stop works
- [x] restart works
- [x] stale state works
- [x] backend outage handled
- [x] tests pass
- [x] Docker build passes
- [x] raw datasets and PCAPs are ignored/not tracked

Known limitations:

- Docker compose defaults to mock telemetry; host Npcap capture is not passed
  into the container.
- The default dashboard port 8501 was occupied during acceptance; port 8512
  was used for the clean Docker dashboard check.
- Real first-inference timing is traffic-dependent and measured at 296.97
  seconds in the latest run.
