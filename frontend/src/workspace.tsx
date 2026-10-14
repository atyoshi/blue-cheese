import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Check,
  Download,
  MessageSquare,
  X,
  LoaderCircle,
  StopCircle,
  FileText,
  ChevronRight,
} from "lucide-react";
import {
  active,
  label,
  time,
  useResource,
  useStoredState,
  type SavedCase,
  type Status,
  type Activity,
  type EvidencePage,
  type ChatPage,
  type PresentationBlock,
  type ProviderDiagnostics,
} from "./api";
import type { Act, Inspect, Navigate } from "./main";
import {
  Badge,
  Drawer,
  Empty,
  ErrorNotice,
  Json,
  Loading,
  Section,
  Prose,
  tabKeys,
} from "./ui";
import { Timeline, Connections, matches } from "./charts";
import { Records } from "./records";

export default function CaseWorkspace({
  runId,
  revision,
  act,
  navigate,
  inspect,
  status,
  busy,
}: {
  runId: string;
  revision: number;
  act: Act;
  navigate: Navigate;
  inspect: Inspect;
  status?: Status;
  busy: boolean;
}) {
  const resource = useResource<SavedCase>("cases/" + runId);
  const saved = resource.data;
  const activity = useResource<Activity>(
    "cases/" + runId + "/activity",
    active(saved?.status) ? 1000 : 0,
  );
  const [tab, setTab] = useStoredState("case-tab-" + runId, "Findings");
  const [pair, setPair] = useStoredState("case-pair-" + runId, "");
  const [chatOpen, setChatOpen] = useState(false);
  const [narrow, setNarrow] = useState(
    matchMedia("(max-width:1199px)").matches,
  );
  const [evidenceId, setEvidenceId] = useStoredState(
    "case-evidence-" + runId,
    "",
  );
  useEffect(() => {
    const media = matchMedia("(max-width:1199px)");
    const fn = () => setNarrow(media.matches);
    media.addEventListener("change", fn);
    return () => media.removeEventListener("change", fn);
  }, []);
  useEffect(() => {
    resource.refresh();
    activity.refresh();
  }, [revision]);
  useEffect(() => {
    if (activity.data && saved && activity.data.status !== saved.status)
      resource.refresh();
  }, [activity.data?.status, saved?.status]);
  const viewEvidence: Inspect = (id) => {
    setEvidenceId(id);
    inspect(id, runId);
  };
  async function successor() {
    const result = await act("cases", { parent_run_id: runId });
    if (result?.run_id) navigate("cases/" + result.run_id);
    else if (result) navigate("cases");
  }
  async function investigateHost() {
    const result = await act("cases", {
      seed_event_id: saved?.seed_event_id,
      investigation_scope: "host",
    });
    if (result?.run_id) navigate("cases/" + result.run_id);
    else if (result) navigate("cases");
  }
  if (!saved)
    return (
      <>
        <ErrorNotice message={resource.error} retry={resource.refresh} />
        {resource.loading && <Loading />}
      </>
    );
  const report = saved.report;
  const state = activity.data?.status || saved.status;
  return (
    <>
      <button className="back-link" onClick={() => navigate("cases")}>
        <ArrowLeft size={14} />
        Cases
      </button>
      <div className="page-heading case-heading">
        <div>
          <div className="eyebrow">
            Investigation{" "}
            <span className="mono">{saved.run_id.slice(0, 12)}</span>
          </div>
          <h1>{saved.title}</h1>
          <div className="case-header-meta">
            <Badge value={state} />
            <span>{saved.owner || "Unassigned"}</span>
            <span>{time(saved.created_at)}</span>
          </div>
        </div>
        <div className="heading-actions">
          <button
            className={"secondary " + (chatOpen ? "pressed" : "")}
            aria-pressed={chatOpen}
            onClick={() => setChatOpen((v) => !v)}
          >
            <MessageSquare size={16} />
            Ask Blue Cheese
          </button>
          <button
            className="secondary"
            disabled={busy || status?.investigation_pending}
            onClick={successor}
          >
            New revision
            <ArrowRight size={16} />
          </button>
          {state === "FAILED" &&
            saved.seed_event_id &&
            saved.investigation_scope !== "host" && (
              <button
                className="secondary"
                disabled={busy || status?.investigation_pending}
                onClick={investigateHost}
              >
                Investigate source host
                <ArrowRight size={16} />
              </button>
            )}
        </div>
      </div>
      <ErrorNotice message={resource.error} />
      <div className="scope-strip">
        <div>
          <span className="micro">
            {saved.investigation_scope === "host"
              ? "Source host · ±5 minutes"
              : "Target"}
          </span>
          <strong className="mono">
            {saved.investigation_scope === "host"
              ? saved.target_host
              : saved.pairs[0]
                ? saved.pairs[0].source + " → " + saved.pairs[0].destination
                : "Selected evidence"}
          </strong>
        </div>
        <div>
          <span className="micro">Frozen evidence</span>
          <strong>
            {saved.record_count.toLocaleString()} records · {saved.pair_count}{" "}
            {saved.pair_count === 1 ? "pair" : "pairs"}
          </strong>
        </div>
        <div>
          <span className="micro">Evidence window</span>
          <strong>
            {saved.coverage?.time_window?.[0]
              ? time(saved.coverage.time_window[0]) +
                " – " +
                time(saved.coverage.time_window[1] || undefined)
              : "Time unavailable"}
          </strong>
        </div>
        <div>
          <span className="micro">Snapshot</span>
          <strong className="mono" title={saved.snapshot_id}>
            {saved.snapshot_id.slice(0, 12)}
          </strong>
        </div>
        <div>
          <span className="micro">Analyst decision</span>
          <Badge value={saved.disposition} />
        </div>
      </div>
      {active(state) && (
        <div className="run-strip" role="status">
          <LoaderCircle size={17} className="spin" />
          <span>
            <strong>{activity.data?.events.at(-1)?.role || "Starting"}</strong>{" "}
            · {label(activity.data?.events.at(-1)?.status || "queued")}
          </span>
          <span className="tabular">
            {activity.data?.elapsed_seconds.toFixed(1) || "0.0"}s
          </span>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => act("cases/" + runId + "/cancel", {})}
          >
            <StopCircle size={15} />
            Cancel
          </button>
        </div>
      )}
      <div
        className={"case-layout " + (chatOpen && !narrow ? "with-chat" : "")}
      >
        <div className="case-content">
          <div
            className="tabs case-tabs"
            role="tablist"
            aria-label="Case sections"
          >
            {["Findings", "Evidence", "Activity", "Decision"].map((t) => (
              <button
                role="tab"
                tabIndex={tab === t ? 0 : -1}
                onKeyDown={(e) =>
                  tabKeys(
                    e,
                    ["Findings", "Evidence", "Activity", "Decision"],
                    tab,
                    setTab,
                  )
                }
                aria-selected={tab === t}
                aria-controls={"panel-" + t}
                id={"tab-" + t}
                key={t}
                onClick={() => setTab(t)}
              >
                {t}
                {t === "Activity" && active(state) && (
                  <span className="status-dot accent" />
                )}
              </button>
            ))}
          </div>
          <div
            key={tab}
            className="tab-content"
            role="tabpanel"
            id={"panel-" + tab}
            aria-labelledby={"tab-" + tab}
          >
            {tab === "Findings" ? (
              report ? (
                <Findings saved={saved} inspect={viewEvidence} />
              ) : active(state) ? (
                <Empty
                  title="Analysis in progress"
                  detail="Recorded operations are available under Activity."
                >
                  <button onClick={() => setTab("Activity")}>
                    View activity
                    <ArrowRight size={16} />
                  </button>
                </Empty>
              ) : (
                <Empty
                  title={label(state)}
                  detail={saved.error || "No report was saved."}
                >
                  <p>
                    Evidence and recorded activity remain available. Review the
                    failure before creating a new revision.
                  </p>
                  <button
                    className="secondary"
                    onClick={() => setTab("Activity")}
                  >
                    View activity
                  </button>
                </Empty>
              )
            ) : tab === "Evidence" ? (
              <CaseEvidence
                runId={runId}
                inspect={viewEvidence}
                pair={pair}
                setPair={(value) => {
                  setPair(value);
                  setEvidenceId("");
                }}
              />
            ) : tab === "Activity" ? (
              <ActivityView
                activity={activity.data}
                error={activity.error}
                diagnostics={saved.provider_diagnostics}
              />
            ) : (
              <Decision saved={saved} act={act} busy={busy} />
            )}
          </div>
          <details className="audit">
            <summary>Run history and revisions</summary>
            <History saved={saved} navigate={navigate} />
          </details>
        </div>
        {chatOpen && !narrow && (
          <aside className="chat-aside">
            <Chat
              pair={pair}
              navigate={navigate}
              runId={runId}
              tab={tab}
              evidenceId={evidenceId}
              revision={revision}
              act={act}
              inspect={viewEvidence}
              busy={busy}
              close={() => setChatOpen(false)}
            />
          </aside>
        )}
      </div>
      <Drawer
        open={chatOpen && narrow}
        onClose={() => setChatOpen(false)}
        title="Ask Blue Cheese"
        description="Case context"
      >
        <Chat
          pair={pair}
          navigate={navigate}
          runId={runId}
          tab={tab}
          evidenceId={evidenceId}
          revision={revision}
          act={act}
          inspect={viewEvidence}
          busy={busy}
        />
      </Drawer>
    </>
  );
}
function Citations({ ids, inspect }: { ids?: string[]; inspect: Inspect }) {
  return ids?.length ? (
    <div className="citations">
      {ids.map((id, i) => (
        <button
          className="citation"
          key={id}
          data-drawer-return
          onClick={() => inspect(id)}
          title={id}
        >
          <FileText size={12} />
          {i + 1}
          <span className="sr-only">Open evidence {id}</span>
        </button>
      ))}
    </div>
  ) : null;
}
function Findings({ saved, inspect }: { saved: SavedCase; inspect: Inspect }) {
  const r = saved.report!;
  const f = saved.findings!;
  return (
    <div className="section-stack">
      <Section
        title="Assessment"
        extra={
          <Badge
            value={
              f.activity_assessment === "NOT_RECORDED"
                ? r.verdict
                : f.activity_assessment
            }
          />
        }
      >
        <p className="assessment-impact">
          <span className="micro">Observed impact</span>
          <strong>{label(f.observed_impact.status)}</strong>
        </p>
        <p>{f.observed_impact.description}</p>
        <Citations ids={f.observed_impact.citations} inspect={inspect} />
        <details className="inline-details">
          <summary>Evidence limits</summary>
          <p>{f.evidence_completeness}</p>
        </details>
      </Section>
      {!!saved.protocol_observations?.length && (
        <Section
          title="Observed protocol activity"
          extra={<span className="micro">Source records</span>}
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Path</th>
                  <th>Status</th>
                  <th>Response bytes</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {saved.protocol_observations.map((o, i) => (
                  <tr key={o.evidence_id + "-" + i}>
                    <td className="mono">{o.method || "—"}</td>
                    <td className="wrap mono">{o.path || "—"}</td>
                    <td>{o.response_status ?? "—"}</td>
                    <td>{o.response_length_bytes ?? "—"}</td>
                    <td>
                      <Citations ids={[o.evidence_id]} inspect={inspect} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
      <Section
        title="Findings"
        extra={<span className="micro">Assessed · verify citations</span>}
      >
        {r.claims.length ? (
          r.claims.map((claim, i) => (
            <article className="finding" key={i}>
              <span className="finding-number">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <span className="micro">
                  {label(claim.proposition_type || "assessment")}
                </span>
                <p>{claim.text}</p>
                <Citations ids={claim.citations} inspect={inspect} />
                {!!claim.contradicting_ids?.length && (
                  <div className="contradiction">
                    <span className="micro">Contradicting evidence</span>
                    <Citations
                      ids={claim.contradicting_ids}
                      inspect={inspect}
                    />
                  </div>
                )}
                {!!claim.limitations?.length && (
                  <details className="inline-details">
                    <summary>Claim limitations</summary>
                    <ul>
                      {claim.limitations.map((l, j) => (
                        <li key={j}>{l}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </article>
          ))
        ) : (
          <p className="muted">No assessed findings recorded.</p>
        )}
      </Section>
      <Section title="Working hypothesis" extra={<Badge value="UNVERIFIED" />}>
        <p>{r.hypothesis}</p>
        <details className="inline-details">
          <summary>Alternative explanation checked</summary>
          <p>{r.disconfirmation_test}</p>
          <Badge value={r.falsifier?.status} />
          {r.falsifier?.checked && <p>{r.falsifier.checked}</p>}
        </details>
      </Section>
      {!!f.recommended_checks.length && (
        <Section title="Next checks">
          {f.recommended_checks.map((c, i) => (
            <div className="next-check" key={i}>
              <span className="finding-number">{i + 1}</span>
              <div>
                <h3>{c.action}</h3>
                <details className="inline-details">
                  <summary>Context and required source</summary>
                  <p>{c.purpose}</p>
                  <p>{c.required_source}</p>
                </details>
              </div>
            </div>
          ))}
        </Section>
      )}
      {!!(saved.presentation?.case_gaps || r.unresolved).length && (
        <Section title="Open questions">
          <ul className="plain-list">
            {(saved.presentation?.case_gaps || r.unresolved).map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </Section>
      )}
      <details className="audit">
        <summary>Reasoning and retrieval audit</summary>
        <Json
          value={{
            tools: saved.tool_activity,
            budget: r.budget,
            provider: saved.provider_diagnostics || r.provider_activity,
          }}
        />
      </details>
      {!!saved.decision_advice && (
        <details className="audit">
          <summary>Decision advice · uncalibrated</summary>
          <p>
            <Badge value={saved.decision_advice.status} />
          </p>
          {saved.decision_advice.failure_reason && (
            <p>{saved.decision_advice.failure_reason}</p>
          )}
          {Object.entries(saved.decision_advice.answers || {}).map(
            ([question, answer]) => (
              <div key={question}>
                <h3>{label(question)}</h3>
                <p>
                  Model choice: <strong>{label(answer.choice)}</strong>
                </p>
                <table>
                  <caption>Model choice scores · uncalibrated</caption>
                  <thead>
                    <tr>
                      <th>Option</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(answer.probabilities).map(
                      ([option, score]) => (
                        <tr key={option}>
                          <td>{label(option)}</td>
                          <td>{score.toFixed(3)}</td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            ),
          )}
          <details className="inline-details">
            <summary>Diagnostic details</summary>
            <Json value={saved.decision_advice} />
          </details>
        </details>
      )}
      {!!saved.presentation?.run_limitations.length && (
        <Section title="Analysis limits">
          <ul className="plain-list">
            {saved.presentation.run_limitations.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Section>
      )}
      <div className="export-actions">
        <a
          className="button secondary"
          href={"/api/v1/cases/" + saved.run_id + "/report.json"}
          download
        >
          <Download size={16} />
          JSON
        </a>
        <a
          className="button secondary"
          href={"/api/v1/cases/" + saved.run_id + "/report.md"}
          download
        >
          <Download size={16} />
          Markdown
        </a>
      </div>
    </div>
  );
}
function CaseEvidence({
  runId,
  inspect,
  pair,
  setPair,
}: {
  runId: string;
  inspect: Inspect;
  pair: string;
  setPair: (value: string) => void;
}) {
  const resource = useResource<EvidencePage>("cases/" + runId + "/evidence");
  const [bin, setBin] = useStoredState("case-bin-" + runId, "");
  const [kind, setKind] = useStoredState("case-kind-" + runId, "all");
  const data = resource.data;
  const filtered = useMemo(
    () =>
      data?.rows.filter(
        (r) =>
          (kind === "all" || r.event_type === kind) &&
          matches(r, pair, bin, data.summary.bin_minutes),
      ) || [],
    [data, pair, bin, kind],
  );
  return (
    <>
      <ErrorNotice message={resource.error} retry={resource.refresh} />
      {!data ? (
        <Loading />
      ) : (
        <div className="section-stack">
          <div className="view-scope">
            {data.rows.length.toLocaleString()} of{" "}
            {data.total?.toLocaleString()} frozen records
          </div>
          <Timeline summary={data.summary} selected={bin} onSelect={setBin} />
          <Connections
            pairs={data.summary.connections}
            selected={pair}
            onSelect={setPair}
          />
          <Section
            title="Records"
            extra={
              <select
                aria-label="Evidence type"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
              >
                <option value="all">All types</option>
                {[...new Set(data.rows.map((r) => r.event_type))].map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
            }
          >
            <Records
              rows={filtered}
              inspect={inspect}
              stateKey={"case-record-page-" + runId}
            />
          </Section>
        </div>
      )}
    </>
  );
}
function ActivityView({
  activity,
  error,
  diagnostics,
}: {
  activity?: Activity;
  error: string;
  diagnostics?: ProviderDiagnostics;
}) {
  const [role, setRole] = useState("all");
  const events = activity?.events || [];
  const roles = [...new Set(events.map((e) => e.role))];
  const requests = (activity?.provider_diagnostics || diagnostics)?.turns || [];
  return (
    <div className="section-stack">
      <ErrorNotice message={error} />
      <Section
        title="Agent operations"
        extra={
          activity && (
            <span className="micro tabular">
              {activity.elapsed_seconds.toFixed(1)}s elapsed
            </span>
          )
        }
      >
        <div className="agent-stages">
          {roles.map((r) => {
            const event = events.filter((e) => e.role === r).at(-1)!;
            return (
              <div key={r}>
                <strong>{r}</strong>
                <Badge
                  value={
                    !active(activity?.status) &&
                    ["working", "queued", "cancel_requested"].includes(
                      event.status,
                    )
                      ? activity?.status
                      : event.status
                  }
                />
                <span className="micro">{label(event.kind)}</span>
              </div>
            );
          })}
        </div>
        {!events.length && <Empty title="No recorded operations" />}
      </Section>
      <Section
        title="Operation timeline"
        extra={
          <select
            aria-label="Filter activity role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="all">All roles</option>
            {roles.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        }
      >
        <ol className="operation-list">
          {events
            .filter((e) => role === "all" || e.role === role)
            .map((e) => (
              <li key={e.sequence}>
                <span className="operation-time">
                  {e.elapsed_seconds.toFixed(1)}s
                </span>
                <div className="operation-body">
                  <div className="operation-title">
                    <strong>{e.role}</strong>
                    <Badge value={e.status} />
                  </div>
                  <p>{e.message}</p>
                  <div className="micro">
                    {label(e.kind)}
                    {e.returned_count !== undefined
                      ? " · " + e.returned_count + " records"
                      : ""}
                    {e.handoff_to ? " · Next: " + e.handoff_to : ""}
                  </div>
                </div>
              </li>
            ))}
        </ol>
      </Section>
      {!!requests.length && (
        <details className="audit">
          <summary>Model request diagnostics</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Request</th>
                  <th>Role / model</th>
                  <th>Duration</th>
                  <th>Outcome</th>
                  <th>Output tokens</th>
                  <th>Validation</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((turn) => (
                  <tr key={turn.operation_id}>
                    <td>{turn.operation_id}</td>
                    <td className="wrap">
                      {turn.role}
                      <br />
                      {turn.model}
                    </td>
                    <td>
                      {turn.duration_seconds !== undefined
                        ? turn.duration_seconds.toFixed(1) + "s"
                        : "In flight"}
                    </td>
                    <td>{label(turn.outcome || turn.status)}</td>
                    <td>{turn.usage?.completion_tokens ?? "—"}</td>
                    <td>{turn.validation ? label(turn.validation) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
function Decision({
  saved,
  act,
  busy,
}: {
  saved: SavedCase;
  act: Act;
  busy: boolean;
}) {
  const key = "decision-draft-" + saved.run_id;
  const [draft, setDraft] = useState(() => {
    try {
      return (
        JSON.parse(sessionStorage.getItem(key) || "null") || {
          actor: "",
          owner: saved.owner || "",
          disposition: saved.disposition,
          note: "",
        }
      );
    } catch {
      return {
        actor: "",
        owner: saved.owner || "",
        disposition: saved.disposition,
        note: "",
      };
    }
  });
  const [savedNotice, setSavedNotice] = useState(false);
  const history = useResource<
    { created_at: string; actor: string; disposition: string; note: string }[]
  >("cases/" + saved.run_id + "/decisions");
  const update = (k: string, v: string) => {
    const next = { ...draft, [k]: v };
    setDraft(next);
    sessionStorage.setItem(key, JSON.stringify(next));
    setSavedNotice(false);
  };
  return (
    <div className="section-stack">
      <Section title="Analyst decision">
        <form
          className="decision-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const result = await act(
              "cases/" + saved.run_id + "/decisions",
              draft,
            );
            if (result) {
              setSavedNotice(true);
              sessionStorage.removeItem(key);
              history.refresh();
            }
          }}
        >
          <div className="form-grid">
            <label>
              Analyst
              <input
                required
                maxLength={128}
                value={draft.actor}
                onChange={(e) => update("actor", e.target.value)}
                autoComplete="name"
              />
            </label>
            <label>
              Assigned to
              <input
                maxLength={128}
                value={draft.owner}
                onChange={(e) => update("owner", e.target.value)}
              />
            </label>
          </div>
          <label>
            Disposition
            <select
              aria-label="Disposition"
              value={draft.disposition}
              onChange={(e) => update("disposition", e.target.value)}
            >
              {[
                "OPEN",
                "INVESTIGATING",
                "ESCALATED",
                "CLOSED_BENIGN",
                "CLOSED_INCIDENT",
              ].map((v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Notes
            <textarea
              aria-label="Notes"
              rows={5}
              maxLength={8192}
              value={draft.note}
              onChange={(e) => update("note", e.target.value)}
              placeholder="Record the decision and next steps."
            />
          </label>
          <div className="form-footer">
            <span className="micro">Local attribution</span>
            <button
              className="primary"
              disabled={busy || !draft.actor.trim()}
              type="submit"
            >
              {savedNotice ? (
                <>
                  <Check size={16} />
                  Saved
                </>
              ) : (
                <>
                  Save decision
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
          {savedNotice && (
            <p className="save-status" role="status">
              Decision saved
            </p>
          )}
        </form>
      </Section>
      <Section title="Decision history">
        <ErrorNotice message={history.error} />
        {history.data?.length ? (
          <ol className="decision-history">
            {history.data.map((h, i) => (
              <li key={i}>
                <div>
                  <strong>{h.actor}</strong>
                  <Badge value={h.disposition} />
                  <span className="micro">{time(h.created_at)}</span>
                </div>
                {h.note && <p>{h.note}</p>}
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted">No decisions recorded.</p>
        )}
      </Section>
    </div>
  );
}
function History({
  saved,
  navigate,
}: {
  saved: SavedCase;
  navigate: Navigate;
}) {
  const history = useResource<SavedCase[]>("cases");
  return (
    <ul className="history-list">
      {history.data
        ?.filter((c) => c.case_id === saved.case_id)
        .map((c) => (
          <li key={c.run_id}>
            <button
              className="text-button"
              onClick={() => navigate("cases/" + c.run_id)}
            >
              <span className="mono">{c.run_id.slice(0, 12)}</span>
              <ChevronRight size={14} />
            </button>
            <Badge value={c.status} />
            <span className="micro">{time(c.created_at)}</span>
          </li>
        ))}
    </ul>
  );
}
function Chat({
  pair,
  navigate,
  runId,
  tab,
  evidenceId,
  revision,
  act,
  inspect,
  busy,
  close,
}: {
  pair: string;
  navigate: Navigate;
  runId: string;
  tab: string;
  evidenceId: string;
  revision: number;
  act: Act;
  inspect: Inspect;
  busy: boolean;
  close?: () => void;
}) {
  const resource = useResource<ChatPage>("chat?run_id=" + runId, 2000);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const scroll = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  useEffect(() => resource.refresh(), [revision]);
  useEffect(() => {
    if (stick.current && scroll.current)
      scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [resource.data?.messages.length, resource.data?.pending]);
  async function submit(value = message) {
    if (!value.trim() || submitting) return;
    setSubmitting(true);
    const result = await act("chat", {
      message: value,
      run_id: runId,
      page: "Cases",
      task: tab,
      evidence_id: evidenceId,
      ...(pair ? { connection: pair.split("|") } : {}),
    });
    setSubmitting(false);
    if (result) {
      setMessage("");
      stick.current = true;
      resource.refresh();
    }
  }
  const pending = submitting || resource.data?.pending;
  return (
    <div className="chat-panel">
      <div className="chat-heading">
        <div>
          <MessageSquare size={17} />
          <h2>Ask Blue Cheese</h2>
        </div>
        {close && (
          <button
            className="icon-button"
            aria-label="Close chat"
            onClick={close}
          >
            <X size={17} />
          </button>
        )}
      </div>
      <div className="chat-context">
        <span className="status-dot accent" />
        Case context · {tab}
      </div>
      <div
        className="chat-messages"
        ref={scroll}
        onScroll={() => {
          const el = scroll.current!;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
        }}
      >
        {!resource.data?.messages.length && (
          <div className="chat-empty">
            <p>Explore this case.</p>
            <span className="muted">
              Ask about findings, evidence, or next checks.
            </span>
            <div className="suggestions">
              {[
                "Summarize this case",
                "Show the evidence",
                "What should I check next?",
              ].map((s) => (
                <button
                  key={s}
                  disabled={busy || pending}
                  onClick={() => submit(s)}
                >
                  {s}
                  <ArrowUp size={13} />
                </button>
              ))}
            </div>
          </div>
        )}
        {resource.data?.messages.map((m, index) => {
          let result: {
            reply?: string;
            blocks?: PresentationBlock[];
            error?: boolean;
            citations?: string[];
            action?: string;
            argument?: string;
            investigation_scope?: "connection" | "host";
            view?: string;
          } = {};
          if (m.role === "assistant") {
            try {
              result = JSON.parse(m.content);
              if (m.presentation) Object.assign(result, m.presentation);
            } catch {
              result = { reply: m.content };
            }
          }
          const proposal = [
            "investigate",
            "import",
            "follow",
            "stop",
            "test",
          ].includes(result.action || "");
          return (
            <div
              className={"chat-message " + m.role}
              key={m.created_at + index}
            >
              <span className="micro">
                {m.role === "user" ? "You" : "Blue Cheese"}
              </span>
              {m.role === "user" ? (
                <Prose text={m.content} />
              ) : (
                <Prose text={result.reply} blocks={result.blocks} />
              )}
              <Citations ids={result.citations} inspect={inspect} />
              {result.view &&
                ["Network", "Needs attention", "Alerts"].includes(
                  result.view,
                ) && (
                  <button
                    className="text-button"
                    onClick={() =>
                      navigate(result.view === "Network" ? "network" : "alerts")
                    }
                  >
                    Open {result.view === "Network" ? "Network" : "Alerts"}
                    <ArrowRight size={14} />
                  </button>
                )}

              {proposal && index === resource.data!.messages.length - 1 && (
                <div className="proposal">
                  <span className="micro">Proposed action</span>
                  <strong>{label(result.action)}</strong>
                  {result.action === "investigate" &&
                    result.investigation_scope && (
                      <span className="micro">
                        {result.investigation_scope === "host"
                          ? "Source host across destinations · separate frozen snapshot"
                          : "Connection scope · new revision"}
                      </span>
                    )}
                  {result.argument && <p>{result.argument}</p>}
                  <button
                    className="primary"
                    disabled={busy || pending}
                    onClick={async () => {
                      const r = await act("proposals", {
                        run_id: runId,
                        created_at: m.created_at,
                      });
                      if (r?.run_id) navigate("cases/" + r.run_id);
                      if (r) resource.refresh();
                    }}
                  >
                    Run proposed action
                    <ArrowRight size={15} />
                  </button>
                </div>
              )}
            </div>
          );
        })}
        {pending && (
          <div className="chat-wait" role="status">
            <LoaderCircle className="spin" size={15} />
            Request running
            {resource.data?.pending_since &&
              ` · ${Math.max(0, Math.floor((Date.now() - Date.parse(resource.data.pending_since)) / 1000))}s`}
            <button
              className="text-button"
              onClick={() => act("chat/cancel", {})}
              disabled={busy}
            >
              Cancel
            </button>
          </div>
        )}
        <ErrorNotice message={resource.error || resource.data?.error} />
      </div>
      <form
        className="chat-composer"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <label className="sr-only" htmlFor="case-message">
          Message
        </label>
        <textarea
          id="case-message"
          rows={3}
          placeholder="Ask about this case…"
          maxLength={4096}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              if (!pending && !busy) void submit();
            }
          }}
        />
        <div>
          <span className="micro">Enter to send · Shift+Enter for newline</span>
          <button
            className="primary icon-button"
            aria-label="Send message"
            disabled={busy || pending || !message.trim()}
          >
            <ArrowUp size={17} />
          </button>
        </div>
      </form>
    </div>
  );
}
