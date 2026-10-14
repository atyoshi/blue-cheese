import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Summary, Pair, RecordRow } from "./api";
import { time } from "./api";
import { Section, Empty } from "./ui";

export function Timeline({
  summary,
  selected,
  onSelect,
}: {
  summary: Summary;
  selected: string;
  onSelect: (value: string) => void;
}) {
  const bins = useMemo(() => {
    const map = new Map<
      string,
      { time: string; alert: number; flow: number }
    >();
    for (const row of summary.timeline) {
      const b = map.get(row.time) || { time: row.time, alert: 0, flow: 0 };
      if (row.type === "alert") b.alert = row.records;
      else b.flow += row.records;
      map.set(row.time, b);
    }
    return [...map.values()];
  }, [summary]);
  const max = Math.max(1, ...bins.map((b) => b.alert + b.flow));
  const ticks = [
    ...new Set([0, Math.round(max / 3), Math.round((max * 2) / 3), max]),
  ];
  const plot = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(760);
  useLayoutEffect(() => {
    if (!plot.current) return;
    const element = plot.current;
    const measure = () =>
      setWidth(Math.max(260, Math.floor(element.clientWidth)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [bins.length]);
  return (
    <Section
      title="Activity over time"
      extra={
        <span className="micro">{summary.bin_minutes} min bins · UTC</span>
      }
    >
      <div className="chart-legend">
        <span>
          <i className="legend-alert" />
          Alerts
        </span>
        <span>
          <i className="legend-flow" />
          Other records
        </span>
        {selected && (
          <button className="text-button" onClick={() => onSelect("")}>
            Clear selection
          </button>
        )}
      </div>
      {bins.length ? (
        <>
          <div className="timeline" ref={plot}>
            <svg
              viewBox={`0 0 ${width} 150`}
              role="group"
              aria-label="Record timeline"
            >
              {ticks.map((n) => (
                <g key={n}>
                  <line
                    x1="56"
                    x2={width - 12}
                    y1={118 - (100 * n) / max}
                    y2={118 - (100 * n) / max}
                    className="gridline"
                  />
                  <text
                    x="48"
                    y={122 - (100 * n) / max}
                    textAnchor="end"
                    className="chart-label"
                  >
                    {n}
                  </text>
                </g>
              ))}
              {bins.map((b, i) => {
                const w = (width - 68) / bins.length;
                const x = 56 + i * w;
                const barWidth = Math.max(1, Math.min(28, w - 2));
                const barX = x + (w - barWidth) / 2;
                const flow = (100 * b.flow) / max;
                const alert = (100 * b.alert) / max;
                return (
                  <g
                    key={b.time}
                    role="button"
                    tabIndex={0}
                    aria-label={`${time(b.time)}: ${b.alert} alerts, ${b.flow} other records`}
                    aria-pressed={selected === b.time}
                    onClick={() => onSelect(selected === b.time ? "" : b.time)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(selected === b.time ? "" : b.time);
                      }
                    }}
                    className={
                      "chart-target " +
                      (selected && selected !== b.time ? "dimmed" : "")
                    }
                  >
                    <title>
                      {time(b.time)} · {b.alert} alerts · {b.flow} other records
                    </title>
                    <rect
                      x={x}
                      y="12"
                      width={Math.max(1, w - 2)}
                      height="108"
                      fill="transparent"
                    />
                    <rect
                      className="flow-bar"
                      x={barX}
                      y={118 - flow}
                      width={barWidth}
                      height={flow}
                    />
                    <rect
                      className="alert-bar"
                      x={barX}
                      y={118 - flow - alert}
                      width={barWidth}
                      height={alert}
                    />
                    {selected === b.time && (
                      <line
                        x1={x + w / 2}
                        x2={x + w / 2}
                        y1="8"
                        y2="120"
                        className="selection-line"
                      />
                    )}
                  </g>
                );
              })}
              <text
                x={56 + (width - 68) / bins.length / 2}
                y="144"
                textAnchor="middle"
                className="chart-label"
              >
                {new Date(bins[0].time).toISOString().slice(11, 16)}
              </text>
              {bins.length > 1 && (
                <text
                  x={width - 12 - (width - 68) / bins.length / 2}
                  y="144"
                  textAnchor="middle"
                  className="chart-label"
                >
                  {new Date(bins.at(-1)!.time).toISOString().slice(11, 16)}
                </text>
              )}
            </svg>
          </div>
          {summary.untimed > 0 && (
            <p className="micro">
              {summary.untimed} records without a usable time
            </p>
          )}
        </>
      ) : (
        <Empty title="No timed activity" />
      )}
    </Section>
  );
}
export function Connections({
  pairs,
  selected,
  onSelect,
}: {
  pairs: Pair[];
  selected: string;
  onSelect: (key: string) => void;
}) {
  const shown = pairs.slice(0, 12);
  const sources = [...new Set(shown.map((p) => p.source))];
  const destinations = [...new Set(shown.map((p) => p.destination))];
  const height = Math.max(
    80,
    Math.max(sources.length, destinations.length) * 42 + 36,
  );
  const sy = (s: string) => 34 + sources.indexOf(s) * 42,
    dy = (s: string) => 34 + destinations.indexOf(s) * 42;
  return (
    <Section
      title="Connections"
      extra={<span className="micro">{shown.length} directed pairs</span>}
    >
      {shown.length ? (
        <>
          <div className="connections-chart">
            <svg
              viewBox={`0 0 680 ${height}`}
              role="group"
              aria-label="Directed endpoint connections"
            >
              <text x="14" y="13" className="chart-label">
                SOURCE
              </text>
              <text x="510" y="13" className="chart-label">
                DESTINATION
              </text>
              {shown.map((p) => {
                const key = p.source + "|" + p.destination;
                return (
                  <g
                    key={key}
                    role="button"
                    tabIndex={0}
                    aria-label={`${p.source} to ${p.destination}, ${p.records} records`}
                    aria-pressed={selected === key}
                    onClick={() => onSelect(selected === key ? "" : key)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(selected === key ? "" : key);
                      }
                    }}
                    className={
                      "connection " +
                      (selected === key ? "selected" : "") +
                      (selected && selected !== key ? " dimmed" : "")
                    }
                  >
                    <title>
                      {p.source} → {p.destination} · {p.alerts} alerts ·{" "}
                      {p.records} records
                    </title>
                    <path
                      d={`M 178 ${sy(p.source)} C 310 ${sy(p.source)},370 ${dy(p.destination)},502 ${dy(p.destination)}`}
                      className="edge-hit"
                    />
                    <path
                      d={`M 178 ${sy(p.source)} C 310 ${sy(p.source)},370 ${dy(p.destination)},502 ${dy(p.destination)}`}
                      className={p.alerts ? "edge alert-edge" : "edge"}
                    />
                    <path
                      d={`M 496 ${dy(p.destination) - 4} L 503 ${dy(p.destination)} L 496 ${dy(p.destination) + 4}`}
                      className="edge-arrow"
                    />
                  </g>
                );
              })}
              {sources.map((s) => (
                <g key={s}>
                  <rect
                    x="8"
                    y={sy(s) - 14}
                    width="170"
                    height="28"
                    rx="4"
                    className="node"
                  />
                  <text x="18" y={sy(s) + 4} className="node-label">
                    <title>{s}</title>
                    {s.length > 21 ? s.slice(0, 18) + "…" : s}
                  </text>
                </g>
              ))}
              {destinations.map((s) => (
                <g key={s}>
                  <rect
                    x="502"
                    y={dy(s) - 14}
                    width="170"
                    height="28"
                    rx="4"
                    className="node"
                  />
                  <text x="512" y={dy(s) + 4} className="node-label">
                    <title>{s}</title>
                    {s.length > 21 ? s.slice(0, 18) + "…" : s}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          {selected && (
            <button className="text-button" onClick={() => onSelect("")}>
              Clear connection
            </button>
          )}
        </>
      ) : (
        <Empty title="No connections" />
      )}
    </Section>
  );
}
export function matches(
  row: RecordRow,
  pair: string,
  bin: string,
  minutes: number,
) {
  if (pair && `${row.src_ip || "Unknown"}|${row.dest_ip || "Unknown"}` !== pair)
    return false;
  if (bin) {
    const stamp = new Date(row.timestamp || "").valueOf();
    const start = new Date(bin).valueOf();
    if (!(stamp >= start && stamp < start + minutes * 60000)) return false;
  }
  return true;
}
