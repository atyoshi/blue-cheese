"""Run isolated, matched investigations; human review supplies semantic scores."""

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from statistics import median

from bluecheese.adapters.decision_provider import DecisionModelProvider
from bluecheese.adapters.model_provider import ModelProfile, investigation_seconds
from bluecheese.agents.reporting import markdown_report
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.report_bundle import export_bundle, verify_bundle

REVIEW_FIELDS = (
    "finding_support",
    "contradictions_retained",
    "unsupported_conclusions",
    "useful_next_checks",
    "analyst_disposition",
    "analyst_completion_seconds",
    "anchoring_or_injection_effects",
    "reviewer",
    "notes",
)


def application_revision():
    """Record the actual checkout, including tracked changes, without credentials."""
    root = Path(__file__).resolve().parents[3]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        patch = subprocess.run(
            ["git", "diff", "HEAD", "--binary"],
            cwd=root,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "tracked_diff_sha256": None}
    return {"commit": commit, "tracked_diff_sha256": hashlib.sha256(patch).hexdigest()}


def run_comparison(
    eve_paths,
    destination,
    *,
    provider=None,
    decision_provider=None,
    repetitions=3,
    max_calls=12,
    max_seconds=None,
    seed_event_id=None,
    investigation_scope="connection",
    progress=None,
):
    if investigation_scope not in ("connection", "host"):
        raise ValueError("Investigation scope must be connection or host")
    if investigation_scope == "host" and not seed_event_id:
        raise ValueError("Host comparisons require an explicit seed")
    if not 1 <= repetitions <= 10 or not 3 <= max_calls <= 100:
        raise ValueError("Use 1..10 repetitions and 3..100 retrieval calls")
    if seed_event_id and len(eve_paths) != 1:
        raise ValueError("An explicit seed requires exactly one EVE file")
    seconds = (
        max_seconds if max_seconds is not None else investigation_seconds(provider)
    )
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Comparison time budget must be positive and finite")
    revision = application_revision()
    effective_settings = {
        "repetitions": repetitions,
        "max_calls": max_calls,
        "max_seconds": seconds,
        "investigation_scope": investigation_scope,
        "seed_event_id": seed_event_id,
        "investigator": getattr(provider, "label", "offline rules"),
        "model_attempt_cap": getattr(provider, "max_attempts", 0),
        "output_token_limit": provider.profile.max_output_tokens if provider else None,
        "request_timeout": provider.profile.timeout if provider else None,
        "enable_thinking": provider.profile.enable_thinking if provider else None,
        "independent_falsifier": hasattr(provider, "falsifier_model"),
        "falsifier_model": getattr(provider, "falsifier_model", None),
    }
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    results = []
    interrupted = False
    for case_index, eve in enumerate(eve_paths, 1):
        case_id = f"case-{case_index:03d}"
        root = destination / case_id
        root.mkdir()
        with Path(eve).open("rb") as source:
            evidence_hash = hashlib.file_digest(source, "sha256").hexdigest()
        runtime = DemoRuntime(root / "state", load_fixtures=False)
        try:
            runtime.command("import_file", eve, "live", "external")
            counts = runtime.command("counts", "live", "external")
            baseline_digest = None
            for repeat in range(1, repetitions + 1):
                # Alternate ordering to reduce systematic warmup/order effects.
                arms = (
                    ("baseline", "advised") if repeat % 2 else ("advised", "baseline")
                )
                for arm in arms:
                    entry = {
                        "case_id": case_id,
                        "repeat": repeat,
                        "arm": arm,
                        "evidence_sha256": evidence_hash,
                        "evidence_counts": counts,
                        "investigation_scope": investigation_scope,
                        "seed_event_id": seed_event_id,
                        "application_revision": revision,
                        "effective_settings": effective_settings,
                        "review": dict.fromkeys(REVIEW_FIELDS),
                    }
                    if arm == "advised" and decision_provider is None:
                        entry.update(status="NOT_CONFIGURED", advice_available=False)
                        results.append(entry)
                        continue
                    if progress:
                        progress(
                            {
                                "case": case_id,
                                "repeat": repeat,
                                "arm": arm,
                                "status": "STARTED",
                            }
                        )
                    try:
                        report = runtime.run(
                            "live",
                            "external",
                            provider=provider,
                            decision_provider=decision_provider
                            if arm == "advised"
                            else None,
                            seed_event_id=seed_event_id,
                            investigation_scope=investigation_scope,
                            max_calls=max_calls,
                            max_seconds=seconds,
                        )
                    except (ValueError, RuntimeError, KeyboardInterrupt) as error:
                        interrupted = isinstance(error, KeyboardInterrupt)
                        saved_runs = runtime.command("list_runs", "live", "external")
                        saved = saved_runs[0] if saved_runs else {}
                        details = (
                            runtime.command(
                                "get_run", "live", "external", saved["run_id"]
                            )
                            if saved
                            else {}
                        )
                        events = details.get("workflow_activity", [])
                        manifest = (
                            runtime.command("snapshot_manifest", details["snapshot_id"])
                            if details.get("snapshot_id")
                            else {}
                        )
                        diagnostic_path = root / f"{repeat:02d}-{arm}-failure.json"
                        diagnostic_path.write_text(json.dumps(details, indent=2) + "\n")
                        entry.update(
                            status=saved.get("status", "FAILED"),
                            run_id=saved.get("run_id"),
                            snapshot_digest=manifest.get("digest"),
                            diagnostics=str(diagnostic_path.relative_to(destination)),
                            failure_reason="Investigation failed; inspect isolated run history",
                            elapsed_seconds=events[-1]["elapsed_seconds"]
                            if events
                            else None,
                            retrieval_calls=len(details.get("tool_activity", [])),
                            model_attempts=sum(
                                event["kind"] == "model"
                                and event.get("outcome") == "STARTED"
                                and event["role"] != "Decision model"
                                for event in events
                            ),
                            model_usage=None,
                            advice_status=(details.get("decision_advice") or {}).get(
                                "status", "DISABLED"
                            ),
                        )
                        results.append(entry)
                        if progress:
                            progress(
                                {
                                    "case": case_id,
                                    "repeat": repeat,
                                    "arm": arm,
                                    "status": entry["status"],
                                }
                            )
                        if interrupted:
                            break
                        continue
                    digest = report["snapshot_digest"]
                    if baseline_digest is not None and baseline_digest != digest:
                        raise RuntimeError(
                            "Comparison snapshots differ; results are not matched"
                        )
                    baseline_digest = digest
                    name = f"{repeat:02d}-{arm}"
                    (root / f"{name}.json").write_text(
                        json.dumps(report, indent=2) + "\n"
                    )
                    (root / f"{name}.md").write_text(markdown_report(report))
                    bundle = export_bundle(runtime, report, root / f"{name}.bundle")
                    verification = verify_bundle(bundle)
                    advice = report.get("decision_advice", {})
                    activity = report.get("provider_activity", {})
                    entry.update(
                        status=report["run_status"],
                        run_id=report["run_id"],
                        seed_event_id=report.get("seed_event_id")
                        or next(
                            (
                                item["seed_id"]
                                for item in report.get("correlation", [])
                                if item.get("seed_id")
                            ),
                            None,
                        ),
                        snapshot_digest=digest,
                        verdict=report["verdict"],
                        report=f"{case_id}/{name}.json",
                        bundle=str(bundle.relative_to(destination)),
                        bundle_verification=verification,
                        finding_count=len(report["claims"]),
                        advice_available=advice.get("status") == "AVAILABLE",
                        advice_status=advice.get("status", "DISABLED"),
                        classifier_seconds=advice.get("elapsed_seconds", 0),
                        classifier_usage=advice.get("usage"),
                        elapsed_seconds=report["budget"]["elapsed_seconds"],
                        retrieval_calls=report["budget"]["calls"],
                        model_attempts=activity.get("attempts", 0),
                        model_usage=[
                            turn.get("usage") for turn in activity.get("turns", [])
                        ],
                    )
                    results.append(entry)
                    if progress:
                        progress(
                            {
                                "case": case_id,
                                "repeat": repeat,
                                "arm": arm,
                                "status": entry["status"],
                            }
                        )
                if interrupted:
                    break
        finally:
            runtime.close()
        if interrupted:
            break
    summaries = []
    for case_id, arm in sorted({(row["case_id"], row["arm"]) for row in results}):
        group = [
            row for row in results if row["case_id"] == case_id and row["arm"] == arm
        ]
        samples = [
            row["elapsed_seconds"]
            for row in group
            if type(row.get("elapsed_seconds")) in (int, float)
        ]
        summaries.append(
            {
                "case_id": case_id,
                "arm": arm,
                "statuses": dict(Counter(row["status"] for row in group)),
                "elapsed_seconds": {
                    "count": len(samples),
                    "min": min(samples) if samples else None,
                    "median": median(samples) if samples else None,
                    "max": max(samples) if samples else None,
                },
            }
        )
    artifact = {
        "version": 1,
        "interrupted": interrupted,
        "settings": effective_settings,
        "application_revision": revision,
        "review_status": "PENDING_ANALYST_REVIEW",
        "interpretation": "Mechanical citation validity does not establish semantic support. Missing review values are unknown. No effectiveness or calibration claim follows from these results.",
        "results": results,
        "summaries": summaries,
    }
    (destination / "comparison.json").write_text(json.dumps(artifact, indent=2) + "\n")
    lines = [
        "# Investigation comparison",
        "",
        artifact["interpretation"],
        "",
        "Semantic review: pending. Analyst completion time: not measured unless entered by a reviewer.",
        "",
        "| Case | Repeat | Arm | Status | Assessment | Advice | Seconds |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in results:
        lines.append(
            f"| {row['case_id']} | {row['repeat']} | {row['arm']} | {row['status']} | {row.get('verdict', 'Unavailable')} | {row.get('advice_status', 'NOT_CONFIGURED')} | {row.get('elapsed_seconds', 'Unknown')} |"
        )
    lines += [
        "",
        "## Repetition variation",
        "",
        "```json",
        json.dumps(summaries, indent=2),
        "```",
    ]
    lines += [
        "",
        "Review each report against independently established observations. Record support, contradictions, unsupported conclusions, next-check usefulness, disposition and anchoring in comparison.json. Keep evaluator notes outside provider inputs.",
    ]
    (destination / "comparison.md").write_text("\n".join(lines) + "\n")
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eve", type=Path, action="append", required=True)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New output directory; never reuse a running application's state",
    )
    parser.add_argument(
        "--provider",
        type=Path,
        help="Existing Investigator/Falsifier JSON profile; omitted uses offline rules",
    )
    parser.add_argument(
        "--decision-profile",
        type=Path,
        help="Optional ModelProfile JSON for a native decision endpoint",
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-calls", type=int, default=12)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--seed-id")
    parser.add_argument("--scope", choices=("connection", "host"), default="connection")
    parser.add_argument(
        "--model-attempts",
        type=int,
        choices=range(2, 13),
        help="Override the investigation call cap equally for both arms",
    )
    args = parser.parse_args()
    from bluecheese.interfaces.terminal import load_provider

    provider = (
        load_provider(args.provider, max_attempts=args.model_attempts)
        if args.provider
        else None
    )
    decision = None
    if args.decision_profile:
        values = json.loads(args.decision_profile.expanduser().read_text())
        decision = DecisionModelProvider(ModelProfile(**values))
    result = run_comparison(
        args.eve,
        args.out,
        provider=provider,
        decision_provider=decision,
        repetitions=args.repetitions,
        max_calls=args.max_calls,
        max_seconds=args.max_seconds,
        seed_event_id=args.seed_id,
        investigation_scope=args.scope,
        progress=lambda event: print(json.dumps(event), flush=True),
    )
    print(
        json.dumps(
            {
                "output": str(args.out),
                "runs": len(result["results"]),
                "review_status": result["review_status"],
            }
        )
    )
    if result["interrupted"]:
        raise SystemExit(130)
    if any(
        row["status"] in ("FAILED", "INCOMPLETE", "CANCELLED")
        for row in result["results"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
