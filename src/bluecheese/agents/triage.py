"""Inspectable, bounded triage policy. No model is required for the demo."""

from bluecheese.domain.models import TriageResult

POLICY_VERSION = "rules-v1"


class TriageAgent:
    def analyze(self, alert: dict, related: list[dict]) -> TriageResult:
        severity = alert["severity"]
        signature = (alert["signature"] or "").lower()
        priority = "high" if severity == 1 else "medium" if severity == 2 else "low"
        reasons = [
            f"Suricata severity {severity if severity is not None else 'unknown'}."
        ]

        if "info" in signature or "teamviewer" in signature:
            if priority == "high":
                priority = "medium"
            reasons.append(
                "Signature appears informational or describes remote access software."
            )

        supporting = [
            event
            for event in related
            if event["event_type"] in ("flow", "dns", "http", "tls")
        ]
        if supporting:
            reasons.append(
                f"{len(supporting)} related network observation(s) are available for review."
            )
        else:
            reasons.append("No related network observations were found in this import.")

        return TriageResult(
            priority=priority,
            disposition="needs_review",
            rationale=" ".join(reasons),
            evidence_ids=tuple(
                [alert["id"]] + [event["id"] for event in supporting[:5]]
            ),
            limitations=(
                "A signature match does not establish malicious intent.",
                "Related records show activity, not whether the activity was authorized.",
            ),
        )

    def triage_events(self, alerts: list[dict]) -> dict:
        """Presentation candidates; preserve occurrence IDs and separate priority from severity."""
        from bluecheese.agents.correlation import event_time

        groups = {}
        for row in alerts[:20]:
            event = row["normalized"]
            timestamp = event_time(event.get("timestamp"))
            key = (
                row["source"],
                event.get("sensor"),
                event.get("signature_id"),
                event.get("src_ip"),
                event.get("dest_ip"),
                event.get("protocol"),
                int(timestamp.timestamp() // 300) if timestamp else row["id"],
            )
            severity = event.get("severity")
            priority = {1: "high", 2: "medium", 3: "low"}.get(severity, "unknown")
            if key not in groups:
                groups[key] = {
                    "seed_ids": [],
                    "occurrence_count": 0,
                    "priority": priority,
                    "sensor_severities": [],
                    "disposition": "needs_review",
                    "reason": "Sensor alerts require scoped review; priority does not establish compromise.",
                    "asset_importance": "unknown",
                    "time_bucket_seconds": 300,
                }
            group = groups[key]
            group["seed_ids"].append(row["id"])
            group["occurrence_count"] += 1
            group["sensor_severities"].append(severity)
            rank = {"high": 0, "medium": 1, "unknown": 2, "low": 3}
            if rank[priority] < rank[group["priority"]]:
                group["priority"] = priority
        candidates = sorted(
            groups.values(),
            key=lambda item: (
                {"high": 0, "medium": 1, "unknown": 2, "low": 3}[item["priority"]],
                item["seed_ids"][0],
            ),
        )
        return {
            "policy_version": "presentation-triage-v1",
            "candidates": candidates,
            "capped": len(alerts) >= 20,
            "limitations": [
                "At most 20 retrieved alerts are grouped; counts describe visible occurrences.",
                "Asset importance is unavailable; no suppression or automated response is applied.",
            ],
        }
