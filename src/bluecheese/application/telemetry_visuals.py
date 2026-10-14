"""Pure, bounded visual summaries of accepted telemetry records."""

import math
from collections import Counter
from datetime import UTC, datetime


def summarize(rows):
    severity = Counter()
    protocols = Counter()
    connections = {}
    timed = []
    for row in rows:
        kind = row["event_type"]
        if kind == "alert":
            value = row.get("severity")
            severity[
                {1: "1 · High", 2: "2 · Medium", 3: "3 · Low"}.get(value, "Unknown")
            ] += 1
        protocols[row.get("protocol") or "Unknown"] += 1
        key = (row.get("src_ip") or "Unknown", row.get("dest_ip") or "Unknown")
        pair = connections.setdefault(
            key,
            {
                "source": key[0],
                "destination": key[1],
                "records": 0,
                "alerts": 0,
                "flows": 0,
            },
        )
        pair["records"] += 1
        if kind == "alert":
            pair["alerts"] += 1
        elif kind == "flow":
            pair["flows"] += 1
        try:
            moment = datetime.fromisoformat(row["timestamp"])
            if moment.tzinfo is None:
                raise ValueError("No timezone")
            timed.append((moment.timestamp(), kind))
        except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
            pass
    timeline, width = [], 60
    if timed:
        first, last = min(t[0] for t in timed), max(t[0] for t in timed)
        # At most 121 bins, including explicit zero-count gaps.
        width = max(60, math.ceil((last - first) / 120 / 60) * 60)
        start, end = math.floor(first / width) * width, math.floor(last / width) * width
        bins = Counter((math.floor(t / width) * width, kind) for t, kind in timed)
        for stamp in range(int(start), int(end) + 1, width):
            for kind in (
                "alert",
                "flow",
                *sorted({k for _, k in timed} - {"alert", "flow"}),
            ):
                timeline.append(
                    {
                        "time": datetime.fromtimestamp(stamp, UTC).isoformat(),
                        "type": kind,
                        "records": bins[(stamp, kind)],
                    }
                )
    return {
        "timeline": timeline,
        "bin_minutes": width // 60,
        "untimed": len(rows) - len(timed),
        "severities": [
            {"severity": label, "alerts": severity[label]}
            for label in ("1 · High", "2 · Medium", "3 · Low", "Unknown")
        ],
        "protocols": [
            {"protocol": label, "records": count}
            for label, count in sorted(protocols.items(), key=lambda p: (-p[1], p[0]))
        ],
        "connections": sorted(
            connections.values(),
            key=lambda p: (-p["alerts"], -p["records"], p["source"], p["destination"]),
        ),
    }


def rank_endpoints(rows):
    """Count each endpoint once per record, including same-IP flows."""
    endpoints = {}
    for row in rows:
        for ip in {row.get("src_ip"), row.get("dest_ip")} - {None, ""}:
            item = endpoints.setdefault(ip, {"ip": ip, "records": 0, "alerts": 0})
            item["records"] += 1
            item["alerts"] += row["event_type"] == "alert"
    return sorted(
        endpoints.values(),
        key=lambda item: (-item["alerts"], -item["records"], item["ip"]),
    )
