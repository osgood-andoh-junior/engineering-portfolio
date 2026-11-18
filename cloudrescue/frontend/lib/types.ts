export const sections = [
  ["overview", "Overview"], ["services", "Services"], ["incidents", "Incidents"],
  ["metrics", "Monitoring Metrics"], ["simulation", "Fault Simulation"],
  ["dependencies", "Service Dependencies"], ["replay", "Incident Replay"],
  ["evaluation", "Diagnostic Evaluation"], ["recovery", "Recovery Center"],
  ["policy-lab", "Policy Lab"], ["reliability", "Reliability Analytics"],
  ["audit", "Audit History"], ["benchmark-lab", "Benchmark Lab"],
  ["security", "Security Administration"], ["audit-verification", "Audit Verification"],
  ["reliability-report", "Reliability Report"], ["settings", "Settings"],
] as const;
export type Section = typeof sections[number][0];
export type State = "healthy" | "degraded" | "down" | "recovering";
export type Mode = "healthy" | "latency" | "error" | "disconnect";
export type Service = {
  slug: string; name: string; state: State; last_success_at: string | null;
  consecutive_failures: number; failure_started_at: string | null;
};
export type Fault = { mode: Mode; latency_ms: number; updated_at: string };
export type Detail = Service & { fault: Fault | null };
export type Check = {
  id: number; checked_at: string; status_code: number | null; latency_ms: number;
  available: boolean; error: string | null;
};
export type Incident = {
  id: number; service_slug: string; started_at: string; detected_at: string;
  recovery_started_at: string | null; closed_at: string | null; duration_seconds: number;
  detection_seconds: number; recovery_seconds: number | null;
};
export type IncidentDetail = Incident & {
  events: { kind: string; occurred_at: string; check: Check }[];
};
export type Summary = Record<State, number> & {
  total: number; active_incidents: number; last_check_at: string | null;
};
export type Metrics = {
  availability: number | null; checks: number;
  points: { time: string; latency_ms: number | null; error_rate: number; checks: number }[];
};
export type Settings = {
  poll_seconds: number; timeout_seconds: number; max_backoff_seconds: number;
  max_concurrency: number; degraded_ms: number; down_after: number; recover_after: number;
};

export const labels = {
  healthy: "Healthy", degraded: "Degraded", down: "Down", recovering: "Recovering",
  latency: "Increased latency", error: "HTTP 500", disconnect: "Connection failure",
} as const;

export function duration(seconds: number | null) {
  if (seconds === null) return "—";
  const rounded = Math.max(0, Math.round(seconds));
  return rounded < 60 ? rounded + "s" : Math.floor(rounded / 60) + "m " + rounded % 60 + "s";
}
