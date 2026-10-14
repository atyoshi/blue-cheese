import { useEffect } from "react";
import { ExternalLink } from "lucide-react";
import { time, useStoredState, type RecordRow } from "./api";
import type { Inspect } from "./main";
import { Empty } from "./ui";

export function Records({
  rows,
  inspect,
  limit = 50,
  stateKey = null,
}: {
  rows: RecordRow[];
  inspect: Inspect;
  limit?: number;
  stateKey?: string | null;
}) {
  const [page, setPage] = useStoredState(stateKey, 1);
  const shown = rows.slice((page - 1) * limit, page * limit);
  useEffect(
    () =>
      setPage((p) => Math.min(p, Math.max(1, Math.ceil(rows.length / limit)))),
    [rows, limit],
  );
  return rows.length ? (
    <>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Type</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Detail</th>
              <th>
                <span className="sr-only">Evidence</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id}>
                <td className="table-time">{time(r.timestamp)}</td>
                <td>
                  <span className="type-label">
                    {r.event_type.toUpperCase()}
                  </span>
                </td>
                <td className="mono wrap">{r.src_ip || "—"}</td>
                <td className="mono wrap">{r.dest_ip || "—"}</td>
                <td className="wrap">
                  {r.alert_signature || r.protocol || "—"}
                </td>
                <td>
                  <button
                    className="icon-button"
                    data-drawer-return
                    aria-label={"Open evidence " + r.id}
                    onClick={() => inspect(r.id)}
                  >
                    <ExternalLink size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > limit && (
        <div className="pagination">
          <span>
            Page {page} of {Math.ceil(rows.length / limit)}
          </span>
          <div className="button-group">
            <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <button
              disabled={page * limit >= rows.length}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </>
  ) : (
    <Empty title="No matching records" />
  );
}
