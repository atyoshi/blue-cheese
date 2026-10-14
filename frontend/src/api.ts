import { useCallback, useEffect, useState } from "react";

export interface RecordRow {
  id: string;
  timestamp?: string;
  src_ip?: string;
  dest_ip?: string;
  event_type: string;
  alert_signature?: string;
  protocol?: string;
  severity?: number;
  [key: string]: unknown;
}
export interface AlertGroup {
  priority: string;
  occurrence_count: number;
  last_seen: string;
  first_seen: string;
  seed_ids: string[];
  seed: { id: string; normalized: RecordRow };
  run_id?: string;
  run_status?: string;
  disposition?: string;
  owner?: string;
  new_alerts: number;
}
export interface AlertPage {
  total: number;
  page: number;
  snapshot: number;
  groups: AlertGroup[];
}
export interface Status {
  running: boolean;
  status: string;
  source?: string;
  last_accepted?: string;
  counts: {
    accepted: number;
    alerts: number;
    flows: number;
    quarantined: number;
  };
  investigation_pending: boolean;
  active_run_id?: string;
  engine: string;
  chat_pending: boolean;
  [key: string]: unknown;
}
export interface ActivityEvent {
  sequence: number;
  role: string;
  status: string;
  kind: string;
  message: string;
  elapsed_seconds: number;
  returned_count?: number;
  outcome?: string;
  handoff_to?: string;
}
export interface ProviderDiagnostics {
  turns: {
    operation_id: string;
    role: string;
    model: string;
    status: string;
    outcome?: string;
    validation?: string;
    duration_seconds?: number;
    usage?: { completion_tokens?: number | null } | null;
  }[];
}
export interface Activity {
  provider_diagnostics?: ProviderDiagnostics;
  status: string;
  events: ActivityEvent[];
  elapsed_seconds: number;
}
export interface Claim {
  text: string;
  citations: string[];
  proposition_type?: string;
  limitations?: string[];
  contradicting_ids?: string[];
}
export interface Check {
  action: string;
  purpose: string;
  required_source: string;
}
export interface Findings {
  activity_assessment: string;
  observed_impact: { status: string; description: string; citations: string[] };
  evidence_completeness: string;
  recommended_checks: Check[];
}
export interface Report {
  verdict: string;
  hypothesis: string;
  claims: Claim[];
  supporting_ids: string[];
  contradicting_ids: string[];
  unresolved: string[];
  warnings: string[];
  disconfirmation_test: string;
  falsifier?: { status?: string; checked?: string };
  budget?: unknown;
  provider_activity?: unknown;
  [key: string]: unknown;
}
export interface Coverage {
  accepted_types: Record<string, number>;
  time_window?: (string | null)[];
  quarantine_reasons: { reason: string; count: number }[];
  quarantine_scope: string;
}
export interface PresentationBlock {
  title: string;
  kind: "paragraph" | "bullets";
  items: string[];
}
export interface Advice {
  status: string;
  failure_reason?: string;
  answers?: Record<
    string,
    { choice: string; probabilities: Record<string, number> }
  >;
  elapsed_seconds?: number;
}
export interface SavedCase {
  coverage?: Coverage;
  presentation?: {
    case_gaps: string[];
    run_limitations: string[];
    shared_guidance: string[];
  };
  provider_diagnostics?: ProviderDiagnostics;
  run_id: string;
  case_id: string;
  title: string;
  question: string;
  status: string;
  owner?: string;
  disposition: string;
  created_at: string;
  seed_event_id?: string;
  snapshot: number;
  snapshot_id: string;
  record_count: number;
  pair_count: number;
  pairs: { source: string; destination: string; records: number }[];
  report?: Report;
  findings?: Findings;
  error?: string;
  workflow_activity: ActivityEvent[];
  tool_activity?: unknown;
  decision_advice?: Advice;
  protocol_observations?: {
    evidence_id: string;
    method?: string;
    path?: string;
    response_status?: number;
    response_length_bytes?: number;
  }[];
}
export interface Pair {
  source: string;
  destination: string;
  records: number;
  alerts: number;
  flows: number;
}
export interface Summary {
  timeline: { time: string; type: string; records: number }[];
  bin_minutes: number;
  untimed: number;
  connections: Pair[];
  protocols: { protocol: string; records: number }[];
  severities: { severity: string; alerts: number }[];
}
export interface EvidencePage {
  rows: RecordRow[];
  summary: Summary;
  total?: number;
  count?: number;
  limit?: number;
  snapshot?: number;
  endpoints?: { ip: string; records: number; alerts: number }[];
}
export interface EvidenceRecord {
  id: string;
  source: string;
  position: number;
  raw: string;
  parsed: unknown;
  normalized: RecordRow;
}
export interface ChatMessage {
  presentation?: { reply: string; blocks: PresentationBlock[] };
  role: string;
  content: string;
  created_at: string;
}
export interface ChatPage {
  messages: ChatMessage[];
  pending: boolean;
  pending_since?: string;
  error?: string;
}
export interface Provider {
  mode: "rules" | "model";
  endpoint?: string;
  model?: string;
  falsifier_model?: string;
  timeout?: number;
  max_output_tokens?: number;
  max_attempts?: number;
  api_key_env?: string;
  has_key?: boolean;
  allow_remote?: boolean;
  allow_insecure_http?: boolean;
  json_mode?: boolean;
  enable_thinking?: boolean | null;
}
export interface Settings {
  coverage?: Coverage;
  provider: Provider;
  decision: Provider;
  automatic: boolean;
  quarantine: { source: string; position: number; error: string }[];
  incidents: {
    created_at?: string;
    diagnostic: string;
    source: string;
    committed_offset: number;
  }[];
  queue: { event_id: string; status: string; [key: string]: unknown }[];
}
let csrf = "";
export async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  if (body !== undefined && !csrf) {
    const session = await fetch("/api/v1/session", { signal });
    if (!session.ok) throw new Error("Unable to open session");
    csrf = (await session.json()).csrf;
  }
  const res = await fetch("/api/v1/" + path, {
    method: body === undefined ? "GET" : "POST",
    signal,
    headers:
      body === undefined
        ? {}
        : { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await res.json();
  if (!res.ok) {
    if (res.status === 403) csrf = "";
    throw new Error(result.error || "Request failed");
  }
  return result;
}
export function useResource<T>(path: string | null, interval = 0) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((r) => r + 1), []);
  useEffect(() => {
    if (!path) {
      setLoading(false);
      return;
    }
    let cancelled = false,
      timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    async function load() {
      try {
        const value = await api<T>(path!, undefined, controller.signal);
        if (!cancelled) {
          setData(value);
          setError("");
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) {
          setLoading(false);
          if (interval) timer = setTimeout(load, interval);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, interval, revision]);
  return { data, error, loading, refresh };
}
export const label = (value?: string) =>
  (value || "Unknown")
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (s) => s.toUpperCase());
export function time(value?: string) {
  if (!value) return "—";
  const d = new Date(value);
  return isNaN(d.valueOf())
    ? value
    : d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      });
}
export const active = (status?: string) =>
  status === "RUNNING" || status === "QUEUED";

export function useStoredState<T>(key: string | null, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      return key
        ? (JSON.parse(sessionStorage.getItem(key) || "null") ?? initial)
        : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    if (key)
      try {
        sessionStorage.setItem(key, JSON.stringify(value));
      } catch {}
  }, [key, value]);
  return [value, setValue] as const;
}
