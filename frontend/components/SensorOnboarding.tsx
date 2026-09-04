import type { SensorSummary } from "../lib/types";

type SetupStep = {
  title: string;
  description: string;
  command?: string;
};

const setupSteps: SetupStep[] = [
  {
    title: "Add Sensor",
    description: "Have an administrator issue a short-lived, one-time enrollment credential on the central service.",
    command: "POST /api/v1/sensors/enrollment · admin-only",
  },
  {
    title: "Install Agent",
    description: "Install the Sentinel agent on the monitored server. Capture stays on that server; raw packets are not sent here.",
    command: "python -m src.agent init --server-url <central-url> --interface \"<interface>\" --environment production",
  },
  {
    title: "Register",
    description: "On the monitored server, consume the enrollment credential once. Registration returns a persistent sensor ID and runtime credential.",
    command: "python -m src.agent register --enrollment-token <one-time-token>",
  },
  {
    title: "Start Agent",
    description: "Validate the protected agent configuration, then start the local process.",
    command: "sentinel-agent config validate\nsentinel-agent start",
  },
  {
    title: "Heartbeat",
    description: "The agent reports process and capture health independently. A heartbeat alone does not make telemetry fresh.",
  },
  {
    title: "Telemetry",
    description: "The agent sends authenticated, aggregated ten-second states. The central service accepts only the existing version-1 telemetry contract.",
    command: "POST /api/v1/telemetry · X-Sentinel-Sensor-Token",
  },
  {
    title: "Sensor Online",
    description: "The central service marks a sensor ONLINE only when heartbeat and telemetry are both fresh.",
  },
];

function stepState(index: number, sensor: SensorSummary | null) {
  if (!sensor) return index === 0 ? "ACTION REQUIRED" : "WAITING";
  if (index === 0 || index === 2) return "COMPLETE";
  if (index === 3 || index === 4) return sensor.agent_status === "ONLINE" ? "OBSERVED" : "WAITING";
  if (index === 5) return sensor.telemetry_status === "FRESH" ? "FRESH" : sensor.telemetry_status === "STALE" ? "STALE" : "WAITING";
  if (sensor.status === "ONLINE") return "ONLINE";
  if (sensor.status === "DEGRADED") return "DEGRADED";
  if (sensor.status === "OFFLINE") return "OFFLINE";
  return "REGISTERED";
}

function stateClass(value: string) {
  return value === "COMPLETE" || value === "OBSERVED" || value === "FRESH" || value === "ONLINE" ? "setup-state setup-state-good" : value === "STALE" || value === "DEGRADED" ? "setup-state setup-state-warn" : value === "OFFLINE" ? "setup-state setup-state-bad" : "setup-state";
}

export function SensorOnboarding({
  sensors,
  selectedSensor,
  onSelectSensor,
  onOpenSensor,
  serverUrl,
  interfaceName,
  onServerUrlChange,
  onInterfaceChange,
}: {
  sensors: SensorSummary[];
  selectedSensor: SensorSummary | null;
  onSelectSensor: (sensorId: string) => void;
  onOpenSensor: () => void;
  serverUrl: string;
  interfaceName: string;
  onServerUrlChange: (value: string) => void;
  onInterfaceChange: (value: string) => void;
}) {
  return (
    <section className="section-block onboarding" aria-labelledby="onboarding-heading">
      <div className="section-heading">
        <div>
          <p className="overline">Operator setup</p>
          <h2 id="onboarding-heading">Connect a monitored server</h2>
          <p className="section-description">Follow the actual agent lifecycle below. Central status is read-only here; only the agent can register, send heartbeats, and deliver telemetry.</p>
        </div>
        <span className="section-note">{selectedSensor ? `tracking ${selectedSensor.hostname}` : "no sensor selected"}</span>
      </div>

      {sensors.length > 0 && (
        <div className="onboarding-sensor-picker">
          <label htmlFor="onboarding-sensor">Sensor to track</label>
          <select id="onboarding-sensor" value={selectedSensor?.sensor_id || ""} onChange={(event) => onSelectSensor(event.target.value)}>
            <option value="" disabled>Select a registered sensor</option>
            {sensors.map((sensor) => <option value={sensor.sensor_id} key={sensor.sensor_id}>{sensor.hostname} · {sensor.status}</option>)}
          </select>
          {selectedSensor && <button className="button-quiet onboarding-detail-button" onClick={onOpenSensor}>Open sensor detail</button>}
        </div>
      )}

      <div className="onboarding-fields">
        <label>Central agent endpoint<input value={serverUrl} onChange={(event) => onServerUrlChange(event.target.value)} placeholder="https://sentinel.example" aria-label="Central agent endpoint" /><small>Use the HTTPS reverse-proxy URL reachable from the monitored server. This page does not register the agent or handle credentials.</small></label>
        <label>Capture interface<input value={interfaceName} onChange={(event) => onInterfaceChange(event.target.value)} aria-label="Capture interface" /></label>
      </div>

      <ol className="setup-timeline">
        {setupSteps.map((step, index) => {
          const state = stepState(index, selectedSensor);
          return <li className="setup-step" key={step.title}>
            <span className="setup-number">{String(index + 1).padStart(2, "0")}</span>
            <div className="setup-copy"><div><strong>{step.title}</strong><span className={stateClass(state)}>{state}</span></div><p>{step.description}</p>{step.command && <pre>{step.command}</pre>}</div>
          </li>;
        })}
      </ol>

      <div className="onboarding-boundary">
        <strong>Credential boundary</strong>
        <span>The browser never issues enrollment credentials or receives runtime secrets. Run the agent commands on the monitored server and use this page to verify the resulting status.</span>
      </div>
    </section>
  );
}
