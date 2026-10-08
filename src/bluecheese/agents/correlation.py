"""Conservative same-source, same-sensor correlation with explicit link bases."""

from datetime import datetime

POLICY_VERSION = "same-source-correlation-v1"


def event_time(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (AttributeError, TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


class CorrelationAgent:
    def __init__(self, window_seconds=300, max_events=100, max_entities=20):
        if (
            not 0 <= window_seconds <= 3600
            or not 1 <= max_events <= 100
            or not 2 <= max_entities <= 100
        ):
            raise ValueError("Invalid bounded correlation policy")
        self.window_seconds = window_seconds
        self.max_events = max_events
        self.max_entities = max_entities

    def correlate(self, seed, candidates):
        anchor = seed["normalized"]
        anchor_time = event_time(anchor.get("timestamp"))
        links, members = [], [seed["id"]]
        entities = {
            value for value in (anchor.get("src_ip"), anchor.get("dest_ip")) if value
        }
        excluded, capped = 0, len(candidates) > self.max_events
        for row in candidates[: self.max_events]:
            if row["id"] == seed["id"]:
                continue
            item = row["normalized"]
            timestamp = event_time(item.get("timestamp"))
            if (
                row["source"] != seed["source"]
                or item.get("sensor") != anchor.get("sensor")
                or anchor_time is None
                or timestamp is None
                or abs((timestamp - anchor_time).total_seconds()) > self.window_seconds
            ):
                excluded += 1
                continue
            endpoints = ("src_ip", "dest_ip", "src_port", "dest_port", "protocol")
            exact_tuple = all(
                anchor.get(key) is not None and item.get(key) == anchor[key]
                for key in endpoints
            )
            same_flow = (
                anchor.get("flow_id") is not None
                and item.get("flow_id") == anchor["flow_id"]
                and all(
                    anchor.get(key) is not None and item.get(key) == anchor[key]
                    for key in ("src_ip", "dest_ip")
                )
            )
            if not same_flow and not exact_tuple:
                excluded += 1
                continue
            proposed_entities = entities | {
                value for value in (item.get("src_ip"), item.get("dest_ip")) if value
            }
            if (
                len(proposed_entities) > self.max_entities
                or len(members) >= self.max_events
            ):
                capped = True
                continue
            entities = proposed_entities
            members.append(row["id"])
            links.append(
                {
                    "seed_id": seed["id"],
                    "event_id": row["id"],
                    "basis": "same_sensor_flow_id_and_endpoints"
                    if same_flow
                    else "exact_endpoint_tuple",
                    "rule_version": POLICY_VERSION,
                    "time_tolerance_seconds": self.window_seconds,
                    "time_difference_seconds": abs(
                        (timestamp - anchor_time).total_seconds()
                    ),
                    "ambiguity": "Association does not establish causality, host ownership or independent corroboration.",
                }
            )
        return {
            "policy_version": POLICY_VERSION,
            "seed_id": seed["id"],
            "member_ids": members,
            "links": links,
            "entities": sorted(entities),
            "excluded_count": excluded,
            "capped": capped,
            "limitations": [
                "Only same-source/sensor records with usable event times are linked.",
                "No transitive, cross-sensor or IP-only merging is performed.",
            ],
        }
