import { StrictMode, Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  Inbox,
  FolderOpen,
  Network,
  Settings as SettingsIcon,
  Moon,
  Sun,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  ArrowUpRight,
  ArrowRight,
  Radio,
  X,
  Search,
  ChevronRight,
  Activity,
  Check,
} from "lucide-react";
import {
  api,
  useResource,
  label,
  time,
  type AlertPage,
  type AlertGroup,
  type Status,
  type SavedCase,
  type EvidenceRecord,
} from "./api";
import {
  Badge,
  Drawer,
  Empty,
  ErrorNotice,
  Hint,
  Guidance,
  Json,
  Loading,
  Pagination,
  tabKeys,
} from "./ui";
import "./style.css";

const CaseWorkspace = lazy(() => import("./workspace"));
const NetworkPage = lazy(() =>
  import("./pages").then((m) => ({ default: m.NetworkPage })),
);
const SettingsPage = lazy(() =>
  import("./pages").then((m) => ({ default: m.SettingsPage })),
);
export interface ActionResult {
  accepted?: boolean;
  investigation?: boolean;
  run_id?: string;
  [key: string]: unknown;
}
export type Act = (path: string, body: unknown) => Promise<ActionResult | null>;
export type Inspect = (id: string, runId?: string, snapshot?: number) => void;
export type Navigate = (path: string) => void;
function initialTheme() {
  try {
    return localStorage.getItem("bluecheese-theme") || "system";
  } catch {
    return "system";
  }
}
function useRoute() {
  const [path, setPath] = useState(location.hash.slice(1) || "alerts");
  useEffect(() => {
    const listener = () => setPath(location.hash.slice(1) || "alerts");
    addEventListener("hashchange", listener);
    return () => removeEventListener("hashchange", listener);
  }, []);
  return path;
}
function App() {
  const route = useRoute();
  const page = route.split("/")[0];
  const runId = page === "cases" ? route.split("/")[1] : undefined;
  const status = useResource<Status>("status", 2000);
  const [theme, setTheme] = useState(initialTheme);
  const [dark, setDark] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [smallNav, setSmallNav] = useState(
    matchMedia("(max-width:899px)").matches,
  );
  useEffect(() => {
    const media = matchMedia("(max-width:899px)");
    const update = () => {
      setSmallNav(media.matches);
      if (!media.matches) setNavOpen(false);
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (!navOpen || !smallNav) return;
    const sidebar = document.querySelector<HTMLElement>(".sidebar")!;
    const previous = document.querySelector<HTMLElement>(".nav-toggle");
    const links = () => [
      ...sidebar.querySelectorAll<HTMLElement>("a[href],button:not(:disabled)"),
    ];
    links()[0]?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const items = links();
      const first = items[0],
        last = items.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [navOpen, smallNav]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [awaitingCase, setAwaitingCase] = useState<string | null>(null);
  const [inspection, setInspection] = useState<{
    id: string;
    runId?: string;
    snapshot?: number;
  }>();
  const evidence = useResource<EvidenceRecord>(
    inspection
      ? "evidence/" +
          encodeURIComponent(inspection.id) +
          "?" +
          new URLSearchParams(
            inspection.runId
              ? { run_id: inspection.runId }
              : {
                  ...(inspection.snapshot !== undefined
                    ? { snapshot: String(inspection.snapshot) }
                    : {}),
                },
          )
      : null,
  );
  const [evidenceTab, setEvidenceTab] = useState("Raw");
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const update = () => {
      const d = theme === "system" ? media.matches : theme === "dark";
      setDark(d);
      document.documentElement.dataset.theme = d ? "dark" : "light";
      document
        .querySelector("meta[name=theme-color]")
        ?.setAttribute("content", d ? "#101318" : "#f5f6f8");
    };
    update();
    media.addEventListener("change", update);
    try {
      localStorage.setItem("bluecheese-theme", theme);
    } catch {}
    return () => media.removeEventListener("change", update);
  }, [theme]);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 3500);
    return () => clearTimeout(t);
  }, [notice]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setNavOpen(false);
    };
    addEventListener("keydown", key);
    return () => removeEventListener("keydown", key);
  }, []);
  const navigate: Navigate = (path) => {
    location.hash = path;
    setNavOpen(false);
  };
  const act: Act = async (path, body) => {
    if (busy) return null;
    setBusy(true);
    setError("");
    try {
      const result = await api<ActionResult>(path, body);
      if (result.investigation && !result.run_id)
        setAwaitingCase(String(status.data?.latest_run_id || ""));
      status.refresh();
      setRevision((r) => r + 1);
      return result;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  };
  const inspect: Inspect = (id, caseId, snapshot) => {
    setEvidenceTab("Raw");
    setInspection({ id, runId: caseId, snapshot });
  };
  const refresh = () => {
    status.refresh();
    setRevision((r) => r + 1);
    setNotice("View refreshed");
  };
  useEffect(() => {
    const id = status.data?.latest_run_id;
    if (
      awaitingCase !== null &&
      typeof id === "string" &&
      id !== awaitingCase
    ) {
      setAwaitingCase(null);
      location.hash = "cases/" + id;
    }
  }, [awaitingCase, status.data?.latest_run_id]);
  const current = status.data;
  const nav = [
    { key: "alerts", title: "Alerts", icon: Inbox },
    { key: "cases", title: "Cases", icon: FolderOpen },
    { key: "network", title: "Network", icon: Network },
  ];
  return (
    <Tooltip.Provider>
      <a
        className="skip-link"
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main")?.focus();
        }}
      >
        Skip to content
      </a>
      <div className="app-shell">
        {navOpen && (
          <button
            className="nav-backdrop"
            aria-label="Close navigation"
            onClick={() => setNavOpen(false)}
          />
        )}
        <aside
          className={"sidebar " + (navOpen ? "open" : "")}
          aria-label="Main navigation"
          aria-hidden={smallNav && !navOpen}
          inert={smallNav && !navOpen}
        >
          <a className="brand" href="#alerts" onClick={() => setNavOpen(false)}>
            <span className="brand-mark">
              B<span />
            </span>
            <span>
              Blue Cheese<span className="brand-sub">ANALYST WORKSPACE</span>
            </span>
          </a>
          <div className="nav-section-label">Workspace</div>
          <nav>
            {nav.map((n) => (
              <a
                key={n.key}
                href={"#" + n.key}
                onClick={() => setNavOpen(false)}
                aria-current={page === n.key ? "page" : undefined}
              >
                <n.icon size={18} />
                <span>{n.title}</span>
                {n.key === "alerts" && current && current.counts.alerts > 0 && (
                  <span className="nav-count">
                    {current.counts.alerts.toLocaleString()}
                  </span>
                )}
                {page === n.key && (
                  <ChevronRight size={14} className="nav-chevron" />
                )}
              </a>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <a
              className={
                "settings-link " + (page === "settings" ? "selected" : "")
              }
              href="#settings"
              onClick={() => setNavOpen(false)}
              aria-current={page === "settings" ? "page" : undefined}
            >
              <SettingsIcon size={18} />
              Settings
            </a>
            <div className="sidebar-status">
              <span
                className={"status-dot " + (current?.running ? "success" : "")}
              />
              <div>
                <strong>
                  {current?.running ? "Source connected" : "Source offline"}
                </strong>
                <span>{current?.engine || "Local workspace"}</span>
              </div>
            </div>
          </div>
        </aside>
        <div className="app-main" inert={smallNav && navOpen}>
          <header className="topbar">
            <div className="topbar-left">
              <button
                className="icon-button nav-toggle"
                aria-label="Open navigation"
                onClick={() => setNavOpen((v) => !v)}
              >
                {navOpen ? <PanelLeftClose /> : <PanelLeftOpen />}
              </button>
              <span className="breadcrumb">
                Workspace <ChevronRight size={14} />{" "}
                <strong>{label(page)}</strong>
                {runId && (
                  <>
                    <ChevronRight size={14} />
                    <span>Investigation</span>
                  </>
                )}
              </span>
            </div>
            <div className="topbar-actions">
              <a
                className="source-indicator"
                href="#settings"
                aria-label="Source connection settings"
              >
                <Radio size={14} />
                <span>{current?.running ? "Connected" : "Offline"}</span>
              </a>
              <span className="toolbar-separator" />
              <Hint text="Refresh view">
                <button
                  className="icon-button"
                  aria-label="Refresh view"
                  onClick={refresh}
                >
                  <RefreshCw className={status.loading ? "spin" : ""} />
                </button>
              </Hint>
              <Hint
                text={dark ? "Switch to light theme" : "Switch to dark theme"}
              >
                <button
                  className="icon-button"
                  aria-label={
                    dark ? "Switch to light theme" : "Switch to dark theme"
                  }
                  onClick={() => setTheme(dark ? "light" : "dark")}
                >
                  {dark ? <Sun /> : <Moon />}
                </button>
              </Hint>
            </div>
          </header>
          <main id="main" tabIndex={-1}>
            <ErrorNotice message={error || status.error} />
            {current?.investigation_pending && page !== "cases" && (
              <div className="notice">
                <Activity size={17} />
                <span>Investigation running</span>
                <button
                  className="text-button"
                  onClick={() =>
                    navigate(
                      current.active_run_id
                        ? "cases/" + current.active_run_id
                        : "cases",
                    )
                  }
                >
                  Open
                  <ArrowUpRight size={15} />
                </button>
              </div>
            )}
            <Suspense fallback={<Loading />}>
              {page === "alerts" ? (
                <Alerts
                  revision={revision}
                  act={act}
                  navigate={navigate}
                  inspect={inspect}
                  status={current}
                  busy={busy}
                />
              ) : page === "cases" ? (
                runId ? (
                  <CaseWorkspace
                    key={runId}
                    runId={runId}
                    revision={revision}
                    act={act}
                    navigate={navigate}
                    inspect={inspect}
                    status={current}
                    busy={busy}
                  />
                ) : (
                  <Cases revision={revision} navigate={navigate} />
                )
              ) : page === "network" ? (
                <NetworkPage revision={revision} inspect={inspect} />
              ) : page === "settings" ? (
                <SettingsPage
                  revision={revision}
                  act={act}
                  status={current}
                  busy={busy}
                  theme={theme}
                  setTheme={setTheme}
                />
              ) : (
                <Empty title="Page not found">
                  <button onClick={() => navigate("alerts")}>
                    Open alerts
                  </button>
                </Empty>
              )}
            </Suspense>
          </main>
          <Guidance />
          <footer className="workspace-footer">
            <span>
              <span className="status-dot" />
              Local workspace
            </span>
            <span>Blue Cheese</span>
          </footer>
        </div>
      </div>
      {notice && (
        <div className="toast" role="status">
          <Check size={16} />
          {notice}
        </div>
      )}
      <Drawer
        open={!!inspection}
        onClose={() => setInspection(undefined)}
        title="Evidence"
        description={inspection?.id}
        wide
      >
        {evidence.loading ? (
          <Loading />
        ) : (
          <>
            <ErrorNotice message={evidence.error} retry={evidence.refresh} />
            {evidence.data && (
              <>
                <dl className="metadata">
                  <div>
                    <dt>Source</dt>
                    <dd>{evidence.data.source}</dd>
                  </div>
                  <div>
                    <dt>Byte offset</dt>
                    <dd>{evidence.data.position}</dd>
                  </div>
                </dl>
                <div
                  className="tabs"
                  role="tablist"
                  aria-label="Evidence representation"
                >
                  {["Raw", "Parsed", "Normalized"].map((t) => (
                    <button
                      key={t}
                      role="tab"
                      tabIndex={evidenceTab === t ? 0 : -1}
                      onKeyDown={(e) =>
                        tabKeys(
                          e,
                          ["Raw", "Parsed", "Normalized"],
                          evidenceTab,
                          setEvidenceTab,
                        )
                      }
                      aria-selected={t === evidenceTab}
                      onClick={() => setEvidenceTab(t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>
                <div role="tabpanel" aria-label={evidenceTab}>
                  <Json
                    value={
                      evidenceTab === "Raw"
                        ? evidence.data.raw
                        : evidenceTab === "Parsed"
                          ? evidence.data.parsed
                          : evidence.data.normalized
                    }
                  />
                </div>
              </>
            )}
          </>
        )}
      </Drawer>
    </Tooltip.Provider>
  );
}
function Alerts({
  revision,
  act,
  navigate,
  inspect,
  status,
  busy,
}: {
  revision: number;
  act: Act;
  navigate: Navigate;
  inspect: Inspect;
  status?: Status;
  busy: boolean;
}) {
  const [page, setPage] = useState(1);
  const [snapshot, setSnapshot] = useState<number>();
  const resource = useResource<AlertPage>(
    "alerts?" +
      new URLSearchParams({
        page: String(page),
        ...(snapshot !== undefined ? { snapshot: String(snapshot) } : {}),
      }),
  );
  const [selected, setSelected] = useState<AlertGroup>();
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("all");
  const [actionBusy, setActionBusy] = useState(false);
  useEffect(() => {
    setSnapshot(undefined);
    resource.refresh();
  }, [revision]);
  useEffect(() => {
    if (resource.data && snapshot === undefined)
      setSnapshot(resource.data.snapshot);
  }, [resource.data, snapshot]);
  const data = resource.data;
  const groups = (data?.groups || []).filter(
    (g) =>
      (priority === "all" || g.priority === priority) &&
      JSON.stringify(g.seed.normalized)
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  async function investigate(group: AlertGroup) {
    setActionBusy(true);
    const result = await act(
      "cases",
      group.run_id
        ? { parent_run_id: group.run_id }
        : { seed_event_id: group.seed_ids[0] },
    );
    setActionBusy(false);
    if (result) {
      setSelected(undefined);
      if (result.run_id) navigate("cases/" + result.run_id);
      else navigate("cases");
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Review queue</div>
          <h1>
            Alerts
            <span className="heading-count">
              {data?.total.toLocaleString() || "0"}
            </span>
          </h1>
          <p>Prioritize. Investigate. Decide.</p>
        </div>
        <button className="secondary" onClick={() => navigate("settings")}>
          <Radio size={16} />
          {status?.running ? "Manage source" : "Connect source"}
        </button>
      </div>
      <div className="queue-summary">
        <div>
          <span className="summary-label">Stored alerts</span>
          <strong>{status?.counts.alerts?.toLocaleString() || "0"}</strong>
        </div>
        <div>
          <span className="summary-label">Accepted records</span>
          <strong>{status?.counts.accepted?.toLocaleString() || "0"}</strong>
        </div>
        <div>
          <span className="summary-label">Source</span>
          <strong className="summary-status">
            <span
              className={"status-dot " + (status?.running ? "success" : "")}
            />
            {status?.running ? "Connected" : "Offline"}
          </strong>
        </div>
        <div>
          <span className="summary-label">Last received</span>
          <strong className="summary-time">
            {time(status?.last_accepted)}
          </strong>
        </div>
      </div>
      <div className="panel queue-panel">
        <div className="table-toolbar">
          <div className="search-field">
            <Search size={16} />
            <input
              aria-label="Filter visible alerts"
              placeholder="Filter this page…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search && (
              <button
                className="icon-button"
                aria-label="Clear filter"
                onClick={() => setSearch("")}
              >
                <X size={14} />
              </button>
            )}
          </div>
          <select
            aria-label="Priority on this page"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
          >
            <option value="all">All priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <span className="toolbar-note">Groups on this 20-alert page</span>
        </div>
        <ErrorNotice message={resource.error} retry={resource.refresh} />
        {resource.loading && !data ? (
          <Loading />
        ) : !data?.total ? (
          <Empty
            title="No alerts yet"
            detail="Connect an EVE source to begin reviewing activity."
          >
            <button className="primary" onClick={() => navigate("settings")}>
              Connect source
              <ArrowRight size={16} />
            </button>
          </Empty>
        ) : groups.length ? (
          <div className="table-scroll">
            <table className="alert-table">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Detection / endpoints</th>
                  <th>Occurrences</th>
                  <th>Last seen</th>
                  <th>Case</th>
                  <th>
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => (
                  <tr
                    key={g.seed.id}
                    className={
                      selected?.seed.id === g.seed.id ? "selected" : ""
                    }
                  >
                    <td>
                      <Badge value={g.priority} />
                    </td>
                    <td>
                      <button
                        className="row-title"
                        data-drawer-return
                        onClick={() => setSelected(g)}
                      >
                        {g.seed.normalized.alert_signature || "Detection alert"}
                      </button>
                      <div className="endpoint-line">
                        <span>{g.seed.normalized.src_ip || "Unknown"}</span>
                        <ArrowRight size={12} />
                        <span>{g.seed.normalized.dest_ip || "Unknown"}</span>
                      </div>
                    </td>
                    <td className="tabular">
                      {g.occurrence_count}
                      {g.new_alerts > 0 && (
                        <span className="new-count">+{g.new_alerts} new</span>
                      )}
                    </td>
                    <td className="table-time">{time(g.last_seen)}</td>
                    <td>
                      {g.run_id ? (
                        <Badge value={g.disposition || g.run_status} />
                      ) : (
                        <span className="muted">Unreviewed</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="icon-button"
                        data-drawer-return
                        aria-label={
                          "Open " +
                          (g.seed.normalized.alert_signature || "alert")
                        }
                        onClick={() => setSelected(g)}
                      >
                        <ArrowUpRight size={17} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="No matching alerts"
            detail="Adjust the filters for this page."
          />
        )}
        {data && data.total > 0 && (
          <Pagination
            page={data.page}
            total={data.total}
            size={20}
            onChange={(p) => {
              setPage(p);
              setSelected(undefined);
            }}
          />
        )}
      </div>
      <Drawer
        open={!!selected}
        onClose={() => setSelected(undefined)}
        title="Alert details"
        description="Sensor detection"
      >
        {selected && (
          <>
            <Badge value={selected.priority} priority />
            <h2 className="detail-title">
              {selected.seed.normalized.alert_signature || "Detection alert"}
            </h2>
            <div className="endpoint-card">
              <span className="micro">Source</span>
              <strong>{selected.seed.normalized.src_ip || "Unknown"}</strong>
              <ArrowRight size={18} />
              <span className="micro">Destination</span>
              <strong>{selected.seed.normalized.dest_ip || "Unknown"}</strong>
            </div>
            <dl className="metadata">
              <div>
                <dt>Occurrences on page</dt>
                <dd>{selected.occurrence_count}</dd>
              </div>
              <div>
                <dt>First seen</dt>
                <dd>{time(selected.first_seen)}</dd>
              </div>
              <div>
                <dt>Last seen</dt>
                <dd>{time(selected.last_seen)}</dd>
              </div>
              <div>
                <dt>Scope</dt>
                <dd>Same source and directed pair · ±5 minutes</dd>
              </div>
            </dl>
            <p className="micro">
              Sensor priority indicates review order. Compromise is unconfirmed.
            </p>
            <div className="stack-actions">
              {selected.run_id && (
                <button
                  className="primary"
                  onClick={() => {
                    setSelected(undefined);
                    navigate("cases/" + selected.run_id);
                  }}
                >
                  Open case
                  <ArrowRight size={16} />
                </button>
              )}
              {(!selected.run_id || selected.new_alerts > 0) && (
                <button
                  className="primary"
                  disabled={busy || actionBusy || status?.investigation_pending}
                  onClick={() => investigate(selected)}
                >
                  {actionBusy
                    ? "Starting…"
                    : selected.run_id
                      ? "Analyze new activity"
                      : "Investigate"}
                  <ArrowRight size={16} />
                </button>
              )}
              <button
                onClick={() => {
                  const g = selected;
                  setSelected(undefined);
                  inspect(g.seed.id, undefined, snapshot);
                }}
              >
                View evidence
              </button>
            </div>
          </>
        )}
      </Drawer>
    </>
  );
}
function Cases({
  revision,
  navigate,
}: {
  revision: number;
  navigate: Navigate;
}) {
  const resource = useResource<SavedCase[]>("cases");
  useEffect(() => resource.refresh(), [revision]);
  const [search, setSearch] = useState("");
  const rows = (resource.data || []).filter((c) =>
    (c.title || c.question || "").toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Investigations</div>
          <h1>Cases</h1>
          <p>Findings, evidence, and analyst decisions.</p>
        </div>
        <button className="secondary" onClick={() => navigate("alerts")}>
          Review alerts
          <ArrowRight size={16} />
        </button>
      </div>
      <div className="panel">
        <div className="table-toolbar">
          <div className="search-field">
            <Search size={16} />
            <input
              aria-label="Filter cases"
              placeholder="Find a case…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <ErrorNotice message={resource.error} retry={resource.refresh} />
        {resource.loading && !resource.data ? (
          <Loading />
        ) : rows.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Analysis</th>
                  <th>Decision</th>
                  <th>Owner</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.run_id}>
                    <td>
                      <button
                        className="row-title"
                        onClick={() => navigate("cases/" + c.run_id)}
                      >
                        {c.title || c.question || "Investigation"}
                      </button>
                      <span className="micro mono">
                        {c.run_id.slice(0, 12)}
                      </span>
                    </td>
                    <td>
                      <Badge value={c.status} />
                    </td>
                    <td>
                      <Badge value={c.disposition} />
                    </td>
                    <td>{c.owner || "Unassigned"}</td>
                    <td>{time(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="No cases"
            detail="Choose an alert to start an investigation."
          />
        )}
      </div>
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
