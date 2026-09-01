export type RuntimeStatus =
  | "INITIALIZING"
  | "CAPTURING"
  | "BUILDING_FLOW_HISTORY"
  | "BUILDING_NETWORK_HISTORY"
  | "FORECAST_READY"
  | "STALE"
  | "STOPPED"
  | "ERROR"
  | "UNKNOWN";

export interface ForecastRow {
  step: number;
  horizon_seconds: number;
  timestamp: string;
  score: number;
  warning: boolean;
}

export interface Explanation {
  top_features?: Array<{
    feature: string;
    sensitivity: number;
    contribution?: number;
    time_position?: string;
  }>;
  temporal_positions?: Array<{
    time_position: string;
    sensitivity: number;
    signed_contribution?: number;
  }>;
  interpretation?: string;
}

export interface ForecastPayload {
  status?: string;
  stale?: boolean;
  reference_timestamp?: string | null;
  sequence_length?: number;
  threshold?: number | null;
  operating_mode?: string | null;
  horizons?: ForecastRow[];
  explanation?: Explanation;
}

export interface SourcePriority {
  source_ip: string;
  priority: string;
  measured_reasons?: string;
  priority_points?: number;
  packet_count?: number;
  byte_count?: number;
  unique_destinations?: number;
  unique_destination_ports?: number;
  flow_count?: number;
  activity_features?: Record<string, number>;
}

export interface MitigationRecommendation {
  source_ip: string;
  priority: string;
  recommendation: string;
  simulation_only?: boolean;
  automatic_block?: boolean;
}

export interface LiveTelemetry {
  adapter?: string;
  available?: boolean;
  started?: boolean;
  mode?: string;
  interface?: string | null;
  status?: string;
  event_count?: number;
  flow_count?: number;
  last_event_at?: string | null;
  freshness?: string;
  readiness_state?: RuntimeStatus;
  packet_quality?: {
    packets_seen?: number;
    valid_events?: number;
    ignored_events?: number;
    dropped_events?: number;
  };
}

export interface LiveState {
  valid_state_count?: number;
  buffer_size?: number;
  buffer_required?: number;
  latest_state_timestamp?: string | null;
  accepted_event_count?: number;
  rejected_event_count?: number;
}

export interface LiveResponse {
  telemetry: LiveTelemetry;
  state: LiveState;
  forecast: ForecastPayload;
  source_priorities?: SourcePriority[];
  mitigation?: { simulation_only?: boolean; recommendations?: MitigationRecommendation[] };
  last_error?: string | null;
  forecast_update_count?: number;
}

export interface DemoResponse {
  timestamp: string;
  network_forecast: {
    model_version: string;
    forecast_horizon_seconds: number;
    forecasts: ForecastRow[];
    operating_mode: string;
    threshold: number;
    explanation: Explanation;
    reference_timestamp: string;
  };
  network_status: string;
  source_priorities: SourcePriority[];
  mitigation_recommendations: MitigationRecommendation[];
  processing_time_ms: number;
  state_count: number;
  history_length: number;
  simulation_only: boolean;
  pcap_attribution_validated: boolean;
}

export interface SensorRuntime {
  sensor_id: string;
  history_length?: number;
  history_required?: number;
  state_count?: number;
  forecast_update_count?: number;
  forecast_status?: string;
  latest_state_timestamp?: string | null;
  source_status?: string;
  forecast?: {
    forecast?: ForecastRow[];
    threshold?: number;
    reference_timestamp?: string;
    explanation?: Explanation;
  } | null;
}

export interface SensorSummary {
  sensor_id: string;
  hostname: string;
  agent_version: string;
  status: "ONLINE" | "DEGRADED" | "OFFLINE";
  last_seen?: string | null;
  last_heartbeat?: string | null;
  last_telemetry_at?: string | null;
  telemetry_freshness_seconds?: number | null;
  heartbeat_freshness_seconds?: number | null;
  buffered_item_count?: number;
  last_sequence?: number;
  runtime?: SensorRuntime;
}
