"""Pure, bounded visual summaries of accepted alert/flow records."""

import json
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
        pair["alerts" if kind == "alert" else "flows"] += 1
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
            for kind in ("alert", "flow"):
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


def connection_graph(connections):
    """Graphviz with quoted labels and generated IDs; telemetry cannot inject DOT."""
    lines = [
        "digraph traffic {",
        "rankdir=LR;",
        'bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fillcolor="#eaf2fa", fontcolor="#152c45", color="#7893ab", fontname="sans-serif"];',
        'edge [fontname="sans-serif", fontsize=11];',
    ]
    sources, destinations = {}, {}
    for pair in connections[:12]:
        for address, nodes, prefix in (
            (pair["source"], sources, "s"),
            (pair["destination"], destinations, "d"),
        ):
            if address not in nodes:
                node = prefix + str(len(nodes))
                nodes[address] = node
                lines.append(
                    f"{node} [label={json.dumps(address, ensure_ascii=False)}];"
                )
        alert_word = "alert" if pair["alerts"] == 1 else "alerts"
        flow_word = "flow" if pair["flows"] == 1 else "flows"
        label = f"{pair['alerts']} {alert_word} · {pair['flows']} {flow_word}"
        color = "#d15b38" if pair["alerts"] else "#367eb3"
        width = 1 + min(4, math.log2(pair["records"] + 1))
        lines.append(
            f'{sources[pair["source"]]} -> {destinations[pair["destination"]]} [label={json.dumps(label, ensure_ascii=False)}, color="{color}", fontcolor="{color}", penwidth={width:.1f}];'
        )
    lines.append("}")
    return "\n".join(lines)
