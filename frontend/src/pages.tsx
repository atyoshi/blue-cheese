import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Radio,
  RefreshCw,
  Check,
  LoaderCircle,
  Plug,
  Unplug,
  Palette,
  SlidersHorizontal,
} from "lucide-react";
import {
  label,
  time,
  useResource,
  type EvidencePage,
  type Provider,
  type Settings,
  type Status,
} from "./api";
import type { Act, Inspect } from "./main";
import { Badge, Empty, ErrorNotice, Json, Loading, Section } from "./ui";
import { Connections, Timeline, matches } from "./charts";
import { Records } from "./records";

export function NetworkPage({
  revision,
  inspect,
}: {
  revision: number;
  inspect: Inspect;
}) {
  const [limit, setLimit] = useState(1000);
  const [endpoint, setEndpoint] = useState("");
  const [pair, setPair] = useState("");
  const [bin, setBin] = useState("");
  const resource = useResource<EvidencePage>(
    "network?" + new URLSearchParams({ limit: String(limit), endpoint }),
  );
  useEffect(() => resource.refresh(), [revision]);
  useEffect(() => {
    setPair("");
    setBin("");
  }, [limit, endpoint]);
  const data = resource.data;
  const rows = useMemo(
    () =>
      data?.rows.filter((r) =>
        matches(r, pair, bin, data.summary.bin_minutes),
      ) || [],
    [data, pair, bin],
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Telemetry</div>
          <h1>Network</h1>
          <p>Connections and activity from accepted records.</p>
        </div>
        <button className="secondary" onClick={resource.refresh}>
          <RefreshCw size={16} />
          Refresh evidence
        </button>
      </div>
      <div className="network-controls">
        <label>
          Record window
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            {[250, 1000, 5000].map((v) => (
              <option value={v} key={v}>
                Latest {v.toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        <label>
          Endpoint
          <select
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
          >
            <option value="">All endpoints</option>
            {data?.endpoints?.map((e) => (
              <option key={e.ip} value={e.ip}>
                {e.ip} · {e.alerts} alerts
              </option>
            ))}
          </select>
        </label>
        <span className="view-scope">
          {data?.count?.toLocaleString()} accepted records · snapshot{" "}
          {data?.snapshot}
        </span>
      </div>
      <ErrorNotice message={resource.error} retry={resource.refresh} />
      {!data ? (
        <Loading />
      ) : !data.count ? (
        <Empty
          title="No network evidence"
          detail="Connect an EVE source in Settings."
        />
      ) : (
        <div className="section-stack">
          <Timeline summary={data.summary} selected={bin} onSelect={setBin} />
          <div className="network-grid">
            <Connections
              pairs={data.summary.connections}
              selected={pair}
              onSelect={setPair}
            />
            <Section title="Protocols">
              <div className="protocol-list">
                {data.summary.protocols.map((p) => (
                  <div key={p.protocol}>
                    <div>
                      <strong>{p.protocol}</strong>
                      <span className="tabular">
                        {p.records.toLocaleString()}
                      </span>
                    </div>
                    <div className="protocol-track">
                      <span
                        style={{
                          width:
                            (100 * p.records) /
                              Math.max(
                                1,
                                ...data.summary.protocols.map((x) => x.records),
                              ) +
                            "%",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          </div>
          <Section
            title="Records"
            extra={
              <span className="micro">
                {rows.length.toLocaleString()} in selection
              </span>
            }
          >
            <Records
              rows={rows}
              inspect={(id) => inspect(id, undefined, data.snapshot)}
            />
          </Section>
        </div>
      )}
    </>
  );
}

export function SettingsPage({
  revision,
  act,
  status,
  busy,
  theme,
  setTheme,
}: {
  revision: number;
  act: Act;
  status?: Status;
  busy: boolean;
  theme: string;
  setTheme: (theme: string) => void;
}) {
  const resource = useResource<Settings>("settings");
  useEffect(() => resource.refresh(), [revision]);
  const data = resource.data;
  const [sourcePath, setSourcePath] = useState("");
  const [sourceMode, setSourceMode] = useState("file");
  const [rotation, setRotation] = useState(false);
  const [sourceNotice, setSourceNotice] = useState("");
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Workspace preferences</div>
          <h1>Settings</h1>
          <p>Sources, appearance, and investigation engines.</p>
        </div>
      </div>
      <ErrorNotice message={resource.error} retry={resource.refresh} />
      <div className="settings-stack">
        <Section title="Appearance" extra={<Palette size={18} />}>
          <div className="setting-row">
            <div>
              <h3>Theme</h3>
              <p className="micro">Apply throughout the workspace.</p>
            </div>
            <div className="segmented" role="group" aria-label="Theme">
              {["light", "dark", "system"].map((t) => (
                <button
                  key={t}
                  aria-pressed={theme === t}
                  onClick={() => setTheme(t)}
                >
                  {label(t)}
                </button>
              ))}
            </div>
          </div>
        </Section>
        <Section
          title="Evidence source"
          extra={<Badge value={status?.running ? "CONNECTED" : "OFFLINE"} />}
        >
          <form
            className="settings-form"
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await act("source", {
                action: "connect",
                path: sourcePath,
                mode: sourceMode,
                recover_rotation: rotation,
              });
              if (result) setSourceNotice("Source connected");
            }}
          >
            <div className="form-grid">
              <label>
                Source type
                <select
                  value={sourceMode}
                  onChange={(e) => setSourceMode(e.target.value)}
                  disabled={status?.running}
                >
                  <option value="file">EVE file</option>
                  <option value="unix_stream">Unix stream</option>
                </select>
              </label>
              <label>
                {sourceMode === "file" ? "File path" : "Socket path"}
                <input
                  required
                  value={sourcePath}
                  onChange={(e) => setSourcePath(e.target.value)}
                  placeholder={
                    sourceMode === "file"
                      ? "/path/to/eve.json"
                      : "/path/to/eve.sock"
                  }
                  disabled={status?.running}
                />
              </label>
            </div>
            {sourceMode === "file" && (
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={rotation}
                  onChange={(e) => setRotation(e.target.checked)}
                  disabled={status?.running}
                />
                Recover matching rotated files
              </label>
            )}
            <div className="form-footer">
              <span className="micro">
                {status?.source || "No source selected"}
              </span>
              <div className="button-group">
                {sourceMode === "file" && !status?.running && (
                  <button
                    type="button"
                    disabled={busy || !sourcePath.trim()}
                    onClick={async () => {
                      const r = await act("source", {
                        action: "import",
                        path: sourcePath,
                      });
                      if (r) setSourceNotice("Import completed");
                    }}
                  >
                    Import once
                  </button>
                )}
                {status?.running ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={async () => {
                      if (await act("source", { action: "stop" }))
                        setSourceNotice("Source disconnected");
                    }}
                  >
                    <Unplug size={16} />
                    Disconnect
                  </button>
                ) : (
                  <button
                    type="submit"
                    className="primary"
                    disabled={busy || !sourcePath.trim()}
                  >
                    <Plug size={16} />
                    Connect
                  </button>
                )}
              </div>
            </div>
            {sourceNotice && (
              <p className="save-status" role="status">
                {sourceNotice}
              </p>
            )}
          </form>
          <div className="health-strip">
            <div>
              <span className="micro">Receiver</span>
              <strong>{status?.status || "Offline"}</strong>
            </div>
            <div>
              <span className="micro">Last received</span>
              <strong>{time(status?.last_accepted)}</strong>
            </div>
            <div>
              <span className="micro">Quarantined</span>
              <strong>{status?.counts.quarantined || 0}</strong>
            </div>
          </div>
        </Section>
        {data ? (
          <>
            <ProviderForm
              key="investigator"
              value={data.provider}
              act={act}
              busy={
                busy ||
                !!status?.investigation_pending ||
                !!status?.chat_pending
              }
            />
            <ProviderForm
              key="decision"
              value={data.decision}
              act={act}
              decision
              busy={
                busy ||
                !!status?.investigation_pending ||
                !!status?.chat_pending
              }
            />
            <Section
              title="Automatic investigations"
              extra={<SlidersHorizontal size={18} />}
            >
              <div className="setting-row">
                <div>
                  <h3>Investigate new alerts automatically</h3>
                  <p className="micro">Disabled after restart.</p>
                </div>
                <button
                  className={"switch " + (data.automatic ? "on" : "")}
                  role="switch"
                  aria-checked={data.automatic}
                  aria-label="Automatic investigations"
                  disabled={busy}
                  onClick={() => act("automatic", { enabled: !data.automatic })}
                >
                  <span />
                </button>
              </div>
              <details className="inline-details">
                <summary>Retry queue · {data.queue.length}</summary>
                {data.queue.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Event</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.queue.map((q, i) => (
                          <tr key={i}>
                            <td className="mono wrap">{q.event_id}</td>
                            <td>
                              <Badge value={q.status} />
                            </td>
                            <td>
                              <button
                                disabled={
                                  busy ||
                                  ![
                                    "FAILED",
                                    "INTERRUPTED",
                                    "CANCELLED",
                                    "INCOMPLETE",
                                  ].includes(q.status)
                                }
                                onClick={() =>
                                  act("retry", { event_id: q.event_id })
                                }
                              >
                                Retry
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted">Queue empty.</p>
                )}
              </details>
            </Section>
            <Section title="Source diagnostics">
              {data.coverage && (
                <>
                  <h3>Accepted evidence</h3>
                  <dl className="coverage-counts">
                    {Object.entries(data.coverage.accepted_types).map(
                      ([kind, count]) => (
                        <div key={kind}>
                          <dt>{kind.toUpperCase()}</dt>
                          <dd>{count.toLocaleString()}</dd>
                        </div>
                      ),
                    )}
                  </dl>
                  {!!data.coverage.quarantine_reasons.length && (
                    <div className="coverage-notice">
                      <p>
                        Some input records were not accepted. Empty searches do
                        not establish absence of activity in the original
                        capture.
                      </p>
                      <ul>
                        {data.coverage.quarantine_reasons.map((r, i) => (
                          <li key={i}>
                            {r.reason}: {r.count.toLocaleString()} records
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}

              <details className="inline-details">
                <summary>
                  Quarantine · {data.quarantine.length} latest records
                </summary>
                {data.quarantine.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th>Offset</th>
                          <th>Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.quarantine.map((q, i) => (
                          <tr key={i}>
                            <td className="wrap">{q.source}</td>
                            <td>{q.position}</td>
                            <td className="wrap">{q.error}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted">No quarantined records.</p>
                )}
              </details>
              <details className="inline-details">
                <summary>Source incidents</summary>
                {data.incidents.length ? (
                  <ul className="plain-list">
                    {data.incidents.map((incident, i) => (
                      <li key={i}>
                        <strong>
                          {incident.created_at
                            ? time(incident.created_at)
                            : "Time unavailable"}
                        </strong>
                        <p>{incident.diagnostic}</p>
                        <details>
                          <summary>Source details</summary>
                          <p className="mono wrap">{incident.source}</p>
                          <p>
                            Last committed byte: {incident.committed_offset}
                          </p>
                        </details>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">No source incidents recorded.</p>
                )}
              </details>
            </Section>
          </>
        ) : (
          <Loading />
        )}
      </div>
    </>
  );
}
function ProviderForm({
  value,
  act,
  busy,
  decision = false,
}: {
  value: Provider;
  act: Act;
  busy: boolean;
  decision?: boolean;
}) {
  const [mode, setMode] = useState(value.mode);
  const [endpoint, setEndpoint] = useState(
    value.endpoint || "http://127.0.0.1:8080/v1",
  );
  const [model, setModel] = useState(value.model || "");
  const [key, setKey] = useState("");
  const [env, setEnv] = useState(
    value.api_key_env || "BLUECHEESE_MODEL_API_KEY",
  );
  const [timeout, setTimeoutValue] = useState(
    value.timeout || (decision ? 20 : 300),
  );
  const [tokens, setTokens] = useState(value.max_output_tokens || 2048);
  const [attempts, setAttempts] = useState(value.max_attempts || 6);
  const [falsifier, setFalsifier] = useState(value.falsifier_model || "");
  const [remote, setRemote] = useState(value.allow_remote || false);
  const [insecure, setInsecure] = useState(value.allow_insecure_http || false);
  const [json, setJson] = useState(value.json_mode || false);
  const [thinking, setThinking] = useState(
    value.enable_thinking === undefined || value.enable_thinking === null
      ? "default"
      : value.enable_thinking
        ? "on"
        : "off",
  );
  const [notice, setNotice] = useState("");
  const [checking, setChecking] = useState(false);
  const probe = useResource<{ pending: boolean; result?: unknown }>(
    checking ? "probe" : null,
    checking ? 1000 : 0,
  );
  useEffect(() => {
    if ((probe.data && !probe.data.pending) || probe.error) setChecking(false);
  }, [probe.data, probe.error]);
  return (
    <Section
      title={decision ? "Decision advice" : "Investigation engine"}
      extra={
        <Badge
          value={
            value.mode === "model" ? "MODEL" : decision ? "DISABLED" : "RULES"
          }
        />
      }
    >
      <form
        className="settings-form"
        onSubmit={async (e) => {
          e.preventDefault();
          const payload =
            mode === "rules"
              ? { mode, decision }
              : {
                  mode,
                  decision,
                  endpoint,
                  model,
                  api_key: key,
                  api_key_env: env,
                  timeout,
                  max_output_tokens: tokens,
                  max_attempts: attempts,
                  falsifier_model: falsifier,
                  allow_remote: remote,
                  allow_insecure_http: insecure,
                  json_mode: json,
                  enable_thinking:
                    thinking === "default" ? null : thinking === "on",
                };
          const r = await act("settings", payload);
          if (r) {
            setKey("");
            setNotice("Settings applied");
          }
        }}
      >
        <label>
          Engine
          <select
            value={mode}
            onChange={(e) => {
              setMode(e.target.value as Provider["mode"]);
              setNotice("");
            }}
            disabled={busy}
          >
            <option value="rules">{decision ? "Disabled" : "Rules"}</option>
            <option value="model">Model endpoint</option>
          </select>
        </label>
        {mode === "model" && (
          <>
            <div className="form-grid">
              <label>
                Endpoint
                <input
                  type="url"
                  required
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  disabled={busy}
                />
              </label>
              <label>
                Model
                <input
                  required
                  maxLength={128}
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  disabled={busy}
                />
              </label>
            </div>
            <label>
              API key
              <input
                type="password"
                autoComplete="new-password"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder={value.has_key ? "Key retained" : "Optional"}
                disabled={busy}
              />
            </label>
            <details className="inline-details">
              <summary>Advanced settings</summary>
              <div className="form-grid">
                <label>
                  Key environment variable
                  <input
                    value={env}
                    onChange={(e) => setEnv(e.target.value)}
                    maxLength={128}
                    disabled={busy}
                  />
                </label>
                <label>
                  Request timeout (seconds)
                  <input
                    type="number"
                    min={1}
                    max={600}
                    value={timeout}
                    onChange={(e) => setTimeoutValue(Number(e.target.value))}
                    disabled={busy}
                  />
                </label>
                {!decision && (
                  <>
                    <label>
                      Falsifier model
                      <input
                        value={falsifier}
                        onChange={(e) => setFalsifier(e.target.value)}
                        placeholder="Use investigator model"
                        disabled={busy}
                      />
                    </label>
                    <label>
                      Maximum model calls
                      <input
                        type="number"
                        min={2}
                        max={12}
                        value={attempts}
                        onChange={(e) => setAttempts(Number(e.target.value))}
                        disabled={busy}
                      />
                    </label>
                    <label>
                      Output token limit
                      <input
                        type="number"
                        min={128}
                        max={8192}
                        value={tokens}
                        onChange={(e) => setTokens(Number(e.target.value))}
                        disabled={busy}
                      />
                    </label>
                    <label>
                      Thinking
                      <select
                        value={thinking}
                        onChange={(e) => setThinking(e.target.value)}
                        disabled={busy}
                      >
                        <option value="default">Server default</option>
                        <option value="on">Enabled</option>
                        <option value="off">Disabled</option>
                      </select>
                    </label>
                  </>
                )}
              </div>
              {!decision && (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={json}
                    onChange={(e) => setJson(e.target.checked)}
                    disabled={busy}
                  />
                  Use JSON object output
                </label>
              )}
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={remote}
                  onChange={(e) => setRemote(e.target.checked)}
                  disabled={busy}
                />
                Allow remote evidence processing
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={insecure}
                  onChange={(e) => setInsecure(e.target.checked)}
                  disabled={busy || !remote}
                />
                Allow unencrypted remote HTTP
              </label>
            </details>
          </>
        )}
        <div className="form-footer">
          <span className="micro">
            {decision
              ? "Advisory scores are uncalibrated."
              : "Triage and correlation use rules."}
          </span>
          <div className="button-group">
            <button
              className="secondary"
              type="button"
              disabled={busy || checking || value.mode !== "model"}
              onClick={async () => {
                const r = await act("probe", { decision });
                if (r) setChecking(true);
              }}
            >
              {checking ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <Radio size={16} />
              )}
              Test connection
            </button>
            <button className="primary" disabled={busy} type="submit">
              Apply
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
        {notice && (
          <p className="save-status" role="status">
            <Check size={15} />
            {notice}
          </p>
        )}
        <ErrorNotice message={probe.error} />
        {probe.data?.result !== undefined && (
          <p role="status">
            Capability check:{" "}
            <strong>
              {label(
                (probe.data.result as { status?: string })?.status ||
                  "result available",
              )}
            </strong>
          </p>
        )}
        {probe.data?.result !== undefined && (
          <details className="inline-details">
            <summary>Capability check diagnostics</summary>
            <Json value={probe.data.result} />
          </details>
        )}
      </form>
    </Section>
  );
}
