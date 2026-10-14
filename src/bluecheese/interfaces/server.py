"""Same-origin analyst API and packaged frontend; one runtime owns the state DB."""

import argparse
import hashlib
import hmac
import json
import os
import secrets
import socket
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from jsonschema import ValidationError, validate
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from bluecheese.adapters.agent_provider import AgentModelProvider, completion_endpoint
from bluecheese.adapters.decision_provider import (
    DecisionModelProvider,
    decision_endpoint,
)
from bluecheese.adapters.model_provider import ModelProfile, investigation_seconds
from bluecheese.agents.findings import findings_view, protocol_observations
from bluecheese.agents.reporting import json_report, markdown_report
from bluecheese.application.demo_runtime import DemoRuntime
from bluecheese.application.presentation import (
    chat_history_presentation,
    report_presentation,
)
from bluecheese.application.source_path import readable_eve_path
from bluecheese.application.telemetry_visuals import rank_endpoints, summarize
from bluecheese.application.view_context import ViewContext

SCOPE = ("live", "external")
STATIC = Path(__file__).with_name("static")
DISPOSITIONS = [
    "OPEN",
    "INVESTIGATING",
    "ESCALATED",
    "CLOSED_BENIGN",
    "CLOSED_INCIDENT",
]


def text(maximum=4096, minimum=0):
    return {"type": "string", "minLength": minimum, "maxLength": maximum}


def checked(data, properties, required=()):
    validate(
        data,
        {
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": list(required),
        },
    )
    return data


def integer(value, minimum=1, maximum=9223372036854775807):
    value = int(value)
    if not minimum <= value <= maximum:
        raise ValueError("Value outside allowed range")
    return value


def get_case(runtime, run_id):
    saved = runtime.command("get_run", *SCOPE, run_id)
    if saved is None:
        raise LookupError("Case not found")
    return saved


def start_case(runtime, data):
    checked(
        data,
        {
            "seed_event_id": text(128, 1),
            "parent_run_id": text(128, 1),
            "question": text(4096, 1),
            "investigation_scope": {"type": "string", "enum": ["connection", "host"]},
        },
    )
    settings = {"max_calls": 8, "max_seconds": investigation_seconds(runtime.provider)}
    if data.get("parent_run_id"):
        prior = get_case(runtime, data["parent_run_id"])
        settings.update(
            seed_event_id=prior["seed_event_id"],
            parent_run_id=prior["run_id"],
            question=data.get("question") or prior["question"],
            investigation_scope=prior["investigation_scope"],
        )
        if (
            data.get("investigation_scope", prior["investigation_scope"])
            != prior["investigation_scope"]
        ):
            raise ValueError(
                "A revision preserves scope; start a new host investigation to expand it"
            )
    elif data.get("seed_event_id"):
        event = runtime.command(
            "get_event", *SCOPE, runtime.command("snapshot"), data["seed_event_id"]
        )
        if not event or event["normalized"]["event_type"] != "alert":
            raise ValueError("Select an available alert")
        if data.get("investigation_scope") == "host" and not event["normalized"].get(
            "src_ip"
        ):
            raise ValueError("Host investigation requires a source IP")
        settings["seed_event_id"] = data["seed_event_id"]
        settings["investigation_scope"] = data.get("investigation_scope", "connection")
        if data.get("question"):
            settings["question"] = data["question"]
    else:
        raise ValueError("Select an alert")
    runtime.begin_run(*SCOPE, **settings)
    return {
        "accepted": True,
        "investigation": True,
        "run_id": runtime.activity.snapshot()["run_id"],
    }


def provider_view(provider):
    if not provider:
        return {"mode": "rules"}
    profile = provider.profile
    return {
        "mode": "model",
        "endpoint": profile.endpoint,
        "model": profile.model,
        "api_key_env": profile.api_key_env,
        "has_key": bool(profile.api_key),
        "timeout": profile.timeout,
        "max_output_tokens": profile.max_output_tokens,
        "allow_remote": profile.allow_remote,
        "allow_insecure_http": profile.allow_insecure_http,
        "enable_thinking": profile.enable_thinking,
        "max_attempts": getattr(provider, "max_attempts", 6),
        "json_mode": getattr(provider, "json_mode", False),
        "falsifier_model": getattr(provider, "falsifier_model", ""),
    }


def configure(runtime, data):
    checked(
        data,
        {
            "mode": {"enum": ["rules", "model"]},
            "decision": {"type": "boolean"},
            "endpoint": text(2048, 1),
            "model": text(128),
            "api_key": text(4096),
            "api_key_env": text(128),
            "timeout": {"type": "number", "minimum": 1, "maximum": 600},
            "max_output_tokens": {"type": "integer", "minimum": 128, "maximum": 8192},
            "max_attempts": {"type": "integer", "minimum": 2, "maximum": 12},
            "allow_remote": {"type": "boolean"},
            "allow_insecure_http": {"type": "boolean"},
            "json_mode": {"type": "boolean"},
            "enable_thinking": {"type": ["boolean", "null"]},
            "falsifier_model": text(128),
        },
        ("mode",),
    )
    decision = data.get("decision", False)
    old = runtime.decision_provider if decision else runtime.provider
    provider = None
    if data["mode"] == "model":
        endpoint = data.get("endpoint", "http://127.0.0.1:8080/v1")
        old_view = provider_view(old)
        normalize_endpoint = decision_endpoint if decision else completion_endpoint
        key = data.get("api_key", "")
        if (
            not key
            and old
            and normalize_endpoint(endpoint) == normalize_endpoint(old.profile.endpoint)
            and data.get("api_key_env", "BLUECHEESE_MODEL_API_KEY")
            == old.profile.api_key_env
        ):
            key = old.profile.api_key
        profile = ModelProfile(
            endpoint=normalize_endpoint(endpoint),
            model=data.get("model", ""),
            api_key=key,
            api_key_env=data.get("api_key_env", "BLUECHEESE_MODEL_API_KEY"),
            timeout=data.get(
                "timeout", old_view.get("timeout", 300) if not decision else 20
            ),
            max_output_tokens=data.get("max_output_tokens", 2048),
            allow_remote=data.get("allow_remote", False),
            allow_insecure_http=data.get("allow_insecure_http", False),
            enable_thinking=data.get(
                "enable_thinking", old_view.get("enable_thinking")
            ),
        )
        provider = (
            DecisionModelProvider(profile)
            if decision
            else AgentModelProvider(
                profile,
                max_attempts=data.get("max_attempts", 6),
                json_mode=data.get("json_mode", False),
                falsifier_model=data.get("falsifier_model", ""),
            )
        )
    runtime.configure_provider(provider, decision=decision)
    return provider_view(provider)


def dispatch(request, data):
    runtime = request.app.state.runtime
    path = request.path_params["path"].strip("/").split("/")
    method, query = request.method, request.query_params
    head = path[0]
    if method == "GET":
        if head == "status":
            status = runtime.status()
            return {
                **status,
                "counts": {
                    **runtime.command("telemetry_totals", *SCOPE),
                    "quarantined": status["counts"]["invalid"],
                },
                "latest_run_id": runtime.activity.snapshot()["run_id"],
                "engine": runtime.provider.label if runtime.provider else "Rules",
                "chat_pending": bool(
                    runtime.pending_chat and not runtime.pending_chat.done()
                ),
            }
        if head == "alerts":
            snapshot = integer(query.get("snapshot", runtime.command("snapshot")), 0)
            return {
                **runtime.command(
                    "attention", *SCOPE, snapshot, page=integer(query.get("page", 1))
                ),
                "snapshot": snapshot,
            }
        if head == "records":
            snapshot = integer(query.get("snapshot", runtime.command("snapshot")), 0)
            severity = query.get("severity")
            return {
                **runtime.command(
                    "browse_telemetry",
                    *SCOPE,
                    snapshot,
                    event_type=query.get("type", "all"),
                    ip=query.get("ip", "")[:128],
                    signature=query.get("signature", "")[:512],
                    severity=integer(severity, 1, 3) if severity else None,
                    page=integer(query.get("page", 1)),
                ),
                "snapshot": snapshot,
            }
        if head == "network":
            snapshot = integer(query.get("snapshot", runtime.command("snapshot")), 0)
            limit = integer(query.get("limit", 1000), 1, 5000)
            rows = runtime.command("visual_telemetry", *SCOPE, snapshot, limit=limit)
            endpoint = query.get("endpoint", "")[:128]
            filtered = [
                r
                for r in rows
                if not endpoint or endpoint in (r.get("src_ip"), r.get("dest_ip"))
            ]
            return {
                "snapshot": snapshot,
                "limit": limit,
                "count": len(rows),
                "rows": filtered,
                "summary": summarize(filtered),
                "endpoints": rank_endpoints(rows)[:50],
            }
        if head == "cases":
            if len(path) == 1:
                return runtime.command("list_runs", *SCOPE)
            saved = get_case(runtime, path[1])
            if len(path) == 2:
                saved["coverage"] = runtime.command(
                    "telemetry_coverage",
                    *SCOPE,
                    saved["snapshot"],
                    snapshot_id=saved["snapshot_id"],
                )
                report = saved.get("report")
                if report:
                    saved["findings"] = findings_view(report)
                    saved["presentation"] = report_presentation(report)
                    if "protocol_observations" in report:
                        saved["protocol_observations"] = report["protocol_observations"]
                    else:
                        ids = list(
                            dict.fromkeys(
                                i
                                for t in saved["tool_activity"]
                                for i in t.get("returned_ids", [])
                            )
                        )[:200]
                        rows = [
                            runtime.command(
                                "get_event",
                                *SCOPE,
                                saved["snapshot"],
                                i,
                                snapshot_id=saved["snapshot_id"],
                            )
                            for i in ids
                        ]
                        saved["protocol_observations"] = protocol_observations(
                            [r for r in rows if r]
                        )
                return saved
            if path[2] == "activity":
                live = runtime.activity.snapshot()
                return {
                    "status": saved["status"],
                    "events": saved["workflow_activity"],
                    "provider_diagnostics": saved.get("provider_diagnostics"),
                    "elapsed_seconds": live["elapsed_seconds"]
                    if live["run_id"] == saved["run_id"]
                    else max(
                        (e["elapsed_seconds"] for e in saved["workflow_activity"]),
                        default=0,
                    ),
                }
            if path[2] == "evidence":
                rows = runtime.command("case_evidence", *SCOPE, saved["run_id"])
                return {
                    "rows": rows,
                    "summary": summarize(rows),
                    "total": saved["record_count"],
                }
            if path[2] == "decisions":
                return runtime.command("analyst_history", *SCOPE, saved["run_id"])
            if path[2] in ("report.json", "report.md"):
                if not saved["report"]:
                    raise LookupError("Report not available")
                markdown = path[2].endswith(".md")
                return Response(
                    markdown_report(saved["report"])
                    if markdown
                    else json_report(saved["report"]),
                    media_type="text/markdown" if markdown else "application/json",
                    headers={
                        "Content-Disposition": f'attachment; filename="{saved["run_id"]}.{"md" if markdown else "json"}"'
                    },
                )
        if head == "evidence" and len(path) == 2:
            run_id = query.get("run_id")
            saved = get_case(runtime, run_id) if run_id else None
            snapshot = (
                saved["snapshot"]
                if saved
                else integer(query.get("snapshot", runtime.command("snapshot")), 0)
            )
            event = runtime.command(
                "get_event",
                *SCOPE,
                snapshot,
                path[1],
                snapshot_id=saved["snapshot_id"] if saved else None,
            )
            if not event:
                raise LookupError("Evidence not available in this snapshot")
            return event
        if head == "chat":
            run_id = query.get("run_id") or None
            if run_id:
                get_case(runtime, run_id)
            future = runtime.pending_chat
            return {
                "messages": chat_history_presentation(
                    runtime.command("chat_history", *SCOPE, run_id)
                ),
                "pending_since": getattr(runtime, "chat_started_at", None),
                "pending": bool(future and not future.done()),
                "error": str(future.exception())
                if future and future.done() and future.exception()
                else None,
            }
        if head == "settings":
            return {
                "provider": provider_view(runtime.provider),
                "decision": provider_view(runtime.decision_provider),
                "automatic": runtime.automatic,
                "queue": runtime.command("work_queue"),
                "quarantine": runtime.command("quarantine_records", *SCOPE),
                "coverage": runtime.command(
                    "telemetry_coverage", *SCOPE, runtime.command("snapshot")
                ),
                "incidents": runtime.command("source_incidents"),
            }
        if head == "probe":
            future = request.app.state.probe
            return {
                "pending": bool(future and not future.done()),
                "result": future.result() if future and future.done() else None,
            }
    elif method == "POST":
        if head == "cases":
            if len(path) == 1:
                return start_case(runtime, data)
            saved = get_case(runtime, path[1])
            if len(path) == 3 and path[2] == "cancel":
                checked(data, {})
                if runtime.activity.snapshot()["run_id"] != saved["run_id"]:
                    raise ValueError("This investigation is not active")
                runtime.cancel()
                return {"accepted": True}
            if len(path) == 3 and path[2] == "decisions":
                checked(
                    data,
                    {
                        "actor": text(128, 1),
                        "owner": text(128),
                        "disposition": {"enum": DISPOSITIONS},
                        "note": text(8192),
                    },
                    ("actor", "disposition"),
                )
                runtime.command(
                    "save_case_decision",
                    *SCOPE,
                    saved["run_id"],
                    data["actor"],
                    data.get("owner", ""),
                    data["disposition"],
                    data.get("note", ""),
                )
                return {"saved": True}
        if head == "chat":
            if len(path) == 2 and path[1] == "cancel":
                checked(data, {})
                runtime.cancel_chat()
                return {"accepted": True}
            checked(
                data,
                {
                    "message": text(4096, 1),
                    "run_id": text(128),
                    "page": {"enum": ["Alerts", "Cases", "Network", "Settings"]},
                    "task": text(128),
                    "evidence_id": text(128),
                    "endpoint": text(128),
                    "connection": {
                        "type": "array",
                        "items": text(128, 1),
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                ("message",),
            )
            run_id = data.get("run_id") or None
            saved = get_case(runtime, run_id) if run_id else None
            context = ViewContext(
                page=data.get("page", "Cases"),
                task={
                    "Activity": "Agent activity",
                    "Evidence": "Evidence and connections",
                    "Decision": "Analyst decision",
                }.get(data.get("task"), data.get("task", "Findings")),
                run_id=run_id,
                snapshot=saved["snapshot"] if saved else runtime.command("snapshot"),
                snapshot_id=saved["snapshot_id"] if saved else None,
                evidence_id=data.get("evidence_id", ""),
                endpoint=data.get("endpoint", ""),
                connection=tuple(data["connection"])
                if data.get("connection")
                else None,
            )
            runtime.begin_chat(data["message"], run_id, context)
            return {"accepted": True}
        if head == "proposals":
            checked(
                data, {"run_id": text(128), "created_at": text(128, 1)}, ("created_at",)
            )
            run_id = data.get("run_id") or None
            history = runtime.command("chat_history", *SCOPE, run_id)
            if (
                not history
                or history[-1]["role"] != "assistant"
                or history[-1]["created_at"] != data["created_at"]
            ):
                raise ValueError("Proposal is no longer current")
            result = json.loads(history[-1]["content"])
            action = result.get("action")
            argument = result.get("argument", "")
            if action == "investigate" and run_id:
                prior = get_case(runtime, run_id)
                proposed_scope = result.get(
                    "investigation_scope", prior["investigation_scope"]
                )
                output = start_case(
                    runtime,
                    {
                        **(
                            {
                                "seed_event_id": prior["seed_event_id"],
                                "investigation_scope": "host",
                            }
                            if proposed_scope == "host"
                            and prior["investigation_scope"] != "host"
                            else {"parent_run_id": run_id}
                        ),
                        "question": argument or prior["question"],
                    },
                )
            elif action in ("import", "follow", "stop", "test"):
                from bluecheese.interfaces.terminal import TerminalSession

                lines = []
                TerminalSession(
                    runtime, read=lambda _: "yes", write=lines.append
                ).execute(action, argument)
                output = {"accepted": True, "reply": "\n".join(lines)}
            else:
                raise ValueError("Action is unavailable")
            runtime.command(
                "append_chat",
                *SCOPE,
                run_id,
                "assistant",
                json.dumps(
                    {
                        "reply": output.get("reply", "Investigation started."),
                        "action": "answer",
                        "citations": [],
                    }
                ),
            )
            return output
        if head == "source":
            checked(
                data,
                {
                    "action": {"enum": ["connect", "stop", "import"]},
                    "path": text(4096, 1),
                    "mode": {"enum": ["file", "unix_stream"]},
                    "recover_rotation": {"type": "boolean"},
                },
                ("action",),
            )
            if data["action"] == "stop":
                runtime.stop()
            elif data["action"] == "import":
                from bluecheese.application.ingestion import import_static_eve

                path_value = readable_eve_path(data.get("path", ""))
                if runtime.status()["running"]:
                    raise ValueError("Disconnect the source before importing")
                if path_value.stat().st_size > 16 * 1024 * 1024:
                    raise ValueError("Import limit is 16 MiB; connect the file instead")
                return runtime.database.apply(import_static_eve, path_value)
            else:
                if runtime.status()["running"]:
                    raise ValueError("Disconnect the current source first")
                unix = data.get("mode") == "unix_stream"
                path_value = (
                    Path(data.get("path", "")).expanduser()
                    if unix
                    else readable_eve_path(data.get("path", ""))
                )
                if not runtime.start(
                    path=path_value,
                    replay=False,
                    unix_stream=unix,
                    recover_rotation=data.get("recover_rotation", False),
                ):
                    raise ValueError(runtime.status()["status"])
            return runtime.status()
        if head == "settings":
            return configure(runtime, data)
        if head == "automatic":
            checked(data, {"enabled": {"type": "boolean"}}, ("enabled",))
            runtime.set_automatic(data["enabled"])
            return {"enabled": runtime.automatic}
        if head == "retry":
            checked(data, {"event_id": text(128, 1)}, ("event_id",))
            runtime.command("retry_work", data["event_id"])
            return {"accepted": True}
        if head == "probe":
            checked(data, {"decision": {"type": "boolean"}})
            state = request.app.state
            if state.probe and not state.probe.done():
                raise ValueError("Connection check is running")
            state.probe = state.jobs.submit(
                runtime.test_provider, decision=data.get("decision", False)
            )
            return {"accepted": True}
    raise LookupError("Endpoint not found")


def create_app(state_dir=None, runtime_factory=None):
    secret = secrets.token_bytes(32)

    @asynccontextmanager
    async def lifespan(app):
        factory = runtime_factory or DemoRuntime
        app.state.runtime = factory(
            Path(
                state_dir or os.environ.get("BLUECHEESE_STATE", "bluecheese-operations")
            ),
            load_fixtures=False,
        )
        app.state.mutations = threading.Lock()
        app.state.jobs = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="bluecheese-probe"
        )
        app.state.probe = None
        try:
            yield
        finally:
            app.state.jobs.shutdown(wait=True)
            await run_in_threadpool(app.state.runtime.close)

    def signature(token):
        return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()

    def valid(token):
        parts = token.split(".")
        return len(parts) == 2 and hmac.compare_digest(signature(parts[0]), parts[1])

    async def session(request):
        token = request.cookies.get("bc-session", "")
        if not valid(token):
            nonce = secrets.token_hex(24)
            token = nonce + "." + signature(nonce)
        response = JSONResponse({"csrf": token})
        response.set_cookie(
            "bc-session",
            token,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
        )
        return response

    async def api(request):
        try:
            data = {}
            if request.method == "POST":
                token = request.cookies.get("bc-session", "")
                if not valid(token) or not hmac.compare_digest(
                    token, request.headers.get("x-csrf-token", "")
                ):
                    return JSONResponse(
                        {"error": "Session expired. Reload the page."}, status_code=403
                    )
                origin = request.headers.get("origin")
                if (
                    origin
                    and origin != f"{request.url.scheme}://{request.headers['host']}"
                ):
                    return JSONResponse(
                        {"error": "Origin is not allowed"}, status_code=403
                    )
                if (
                    request.headers.get("content-type", "").split(";")[0]
                    != "application/json"
                ):
                    return JSONResponse(
                        {"error": "JSON body required"}, status_code=415
                    )
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 32768:
                        return JSONResponse(
                            {"error": "Request too large"}, status_code=413
                        )
                data = json.loads(body)

            def work():
                if request.method == "POST":
                    # Nonblocking: a second click must not queue behind a long source operation.
                    if not request.app.state.mutations.acquire(blocking=False):
                        raise RuntimeError("Another action is in progress")
                    try:
                        return dispatch(request, data)
                    finally:
                        request.app.state.mutations.release()
                return dispatch(request, data)

            result = await run_in_threadpool(work)
            return result if isinstance(result, Response) else JSONResponse(result)
        except LookupError as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        except ValidationError:
            return JSONResponse({"error": "Invalid request fields"}, status_code=400)
        except (ValueError, TypeError, OSError) as error:
            return JSONResponse({"error": str(error)}, status_code=400)
        except RuntimeError as error:
            return JSONResponse({"error": str(error)}, status_code=409)

    async def index(request):
        return FileResponse(STATIC / "index.html")

    async def health(request):
        return JSONResponse({"ok": not request.app.state.runtime.closed})

    app = Starlette(
        lifespan=lifespan,
        routes=[
            Route("/health", health),
            Route("/api/v1/session", session),
            Route("/api/v1/{path:path}", api, methods=["GET", "POST"]),
            Route("/", index),
            Mount("/assets", StaticFiles(directory=STATIC / "assets", check_dir=False)),
            Route("/mark.svg", lambda request: FileResponse(STATIC / "mark.svg")),
        ],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"],
    )

    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api") else "no-cache"
        )
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=headers)
    return app


def main():
    parser = argparse.ArgumentParser(description="Blue Cheese analyst interface")
    parser.add_argument("--port", type=int)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not (STATIC / "index.html").exists():
        parser.error(
            "Frontend assets are missing. Run npm ci && npm run build in frontend/."
        )
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("Port must be 1..65535")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    for port in [args.port] if args.port is not None else range(8501, 8601):
        try:
            listener.bind((args.host, port))
            break
        except OSError:
            if args.port is not None or port == 8600:
                listener.close()
                raise
    listener.listen(128)
    address = f"http://127.0.0.1:{listener.getsockname()[1]}"
    print(f"Blue Cheese: {address}", flush=True)
    config = uvicorn.Config(
        create_app(), host=args.host, port=listener.getsockname()[1], workers=1
    )

    class BrowserServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            if self.started and not args.no_browser:
                await run_in_threadpool(webbrowser.open, address)

    try:
        BrowserServer(config).run(sockets=[listener])
    finally:
        listener.close()


if __name__ == "__main__":
    main()
