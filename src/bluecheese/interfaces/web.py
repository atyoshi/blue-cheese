"""Small localhost analyst UI over the same application services as the CLI."""

import html
import json
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from bluecheese.adapters.sqlite_store import EvidenceStore
from bluecheese.application.import_pcap import import_eve, import_pcap
from bluecheese.application.investigate_alert import case_report, triage_alert

ID_PATTERN = re.compile(r'[0-9a-f]{24}\Z')
IMPORT_LOCK = threading.Lock()
STYLE = """
:root {color-scheme:light; font-family:system-ui,sans-serif; background:#f5f7fa; color:#17212f}
body {margin:0; line-height:1.5} header {background:#172838; color:white; padding:1rem 2rem}
header a {color:white; text-decoration:none; margin-right:1.3rem} main {max-width:1100px; margin:2rem auto; padding:0 1rem}
h1,h2,h3 {line-height:1.2} .grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1rem}
.card {background:white; border:1px solid #dce3eb; border-radius:10px; padding:1.2rem; margin-bottom:1rem; overflow:auto}
label {display:block; font-weight:600; margin:.5rem 0 .15rem} input,select {box-sizing:border-box; width:100%; padding:.55rem; border:1px solid #9caaba; border-radius:5px; font:inherit}
button,.button {display:inline-block; background:#1769a5; color:white; border:0; border-radius:5px; padding:.55rem .8rem; margin-top:.7rem; text-decoration:none; font:inherit; cursor:pointer}
a {color:#125f96} table {border-collapse:collapse; width:100%} th,td {text-align:left; padding:.5rem; border-bottom:1px solid #dce3eb; vertical-align:top}
small,.muted {color:#526577} code,pre {font-family:ui-monospace,monospace} pre {white-space:pre-wrap; overflow-wrap:anywhere; background:#f0f3f7; padding:1rem; border-radius:5px}
.badge {display:inline-block; padding:.15rem .45rem; border-radius:4px; background:#e8eef5} .error {border-color:#bb4451; background:#fff2f2}
.context {background:#e8eef5; padding:.65rem 1rem; overflow-wrap:anywhere} .context code {font-size:.9em}
.actions {display:flex; gap:1rem; align-items:center; flex-wrap:wrap} .actions form {display:flex; gap:.6rem; align-items:end; flex-wrap:wrap}
.actions select {width:auto; max-width:100%} .actions button {margin:0} .pagination {display:flex; gap:1rem; align-items:center; margin-top:1rem}
"""


def esc(value):
    return html.escape('' if value is None else str(value), quote=True)


def link(path, label):
    return f'<a href="{esc(path)}">{esc(label)}</a>'


def table(headers, rows):
    head = ''.join(f'<th>{esc(column)}</th>' for column in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def severity_breakdown(rows):
    counts = {row['severity']: row['count'] for row in rows}
    parts = [f'High (1): {counts.get(1, 0)}', f'Medium (2): {counts.get(2, 0)}',
             f'Low (3): {counts.get(3, 0)}']
    other = sum(count for severity, count in counts.items() if severity not in (1, 2, 3))
    if other:
        parts.append(f'Other/unknown: {other}')
    return ' · '.join(parts)


def page(title, content, data_dir):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)} · Blue Cheese</title><style>{STYLE}</style></head>'
            f'<body><header><strong>Blue Cheese</strong> &nbsp; '
            f'{link("/", "Overview")} {link("/alerts", "Alerts")}</header>'
            f'<div class="context">Evidence directory: <code>{esc(data_dir)}</code></div>'
            f'<main><h1>{esc(title)}</h1>{content}</main></body></html>')


def make_handler(data_dir, csrf_token):
    data_dir = Path(data_dir).resolve()

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, title, body):
            encoded = page(title, body, data_dir).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(encoded)

        def redirect(self, path):
            self.send_response(303)
            self.send_header('Location', path)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_GET(self):
            path = urlparse(self.path).path
            try:
                if path == '/':
                    self.overview()
                elif path == '/alerts':
                    self.alerts()
                elif path.startswith('/alerts/'):
                    self.alert_detail(path.split('/')[-1])
                elif path.startswith('/evidence/'):
                    self.evidence(path.split('/')[-1])
                elif path.startswith('/reports/'):
                    self.report(path.split('/')[-1])
                else:
                    self.respond(404, 'Not found', '<p>No such page.</p>')
            except (OSError, ValueError, KeyError) as exc:
                self.respond(400, 'Unable to display page', f'<div class="card error">{esc(exc)}</div>')

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                self.respond(400, 'Invalid request', '<p>Invalid form length.</p>')
                return
            if length < 1 or length > 16384:
                self.respond(413, 'Invalid request', '<p>Form is too large or empty.</p>')
                return
            try:
                fields = parse_qs(self.rfile.read(length).decode('utf-8'), keep_blank_values=True)
            except UnicodeDecodeError:
                self.respond(400, 'Invalid request', '<p>Form must use UTF-8.</p>')
                return
            values = {key: value[0] for key, value in fields.items()}
            if not secrets.compare_digest(values.get('csrf', ''), csrf_token):
                self.respond(403, 'Forbidden', '<p>Form token is invalid.</p>')
                return
            path = urlparse(self.path).path
            try:
                if path == '/imports':
                    source = values.get('path', '').strip()
                    if not source:
                        raise ValueError('Enter a PCAP or EVE path')
                    with IMPORT_LOCK:
                        if values.get('kind') == 'eve':
                            result = import_eve(source, data_dir)
                        elif values.get('kind') == 'pcap':
                            result = import_pcap(source, data_dir,
                                                 config_path=values.get('config') or None,
                                                 rules_path=values.get('rules') or None)
                        else:
                            raise ValueError('Choose PCAP or EVE')
                    self.redirect(f"/alerts?import_id={result['id']}")
                elif path.startswith('/triage/'):
                    event_id = self.valid_id(path.split('/')[-1])
                    triage_alert(data_dir, event_id)
                    self.redirect(f'/reports/{event_id}')
                else:
                    self.respond(404, 'Not found', '<p>No such action.</p>')
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                self.respond(400, 'Action failed', f'<div class="card error">{esc(exc)}</div><p>{link("/", "Back to overview")}</p>')

        @staticmethod
        def valid_id(value):
            if not ID_PATTERN.fullmatch(value):
                raise ValueError('Invalid event ID')
            return value

        def overview(self):
            with EvidenceStore(data_dir / 'bluecheese.sqlite3') as store:
                runs = [dict(row) for row in store.db.execute(
                    "SELECT i.*, a.original_name, a.kind, "
                    "(SELECT COUNT(*) FROM events e WHERE e.import_id=i.id) AS event_count, "
                    "(SELECT COUNT(*) FROM events e WHERE e.import_id=i.id AND e.event_type='alert') AS alert_count "
                    "FROM imports i JOIN artifacts a ON a.id=i.input_artifact_id "
                    "ORDER BY i.started_at DESC LIMIT 20")]
                severity_rows = [dict(row) for row in store.db.execute(
                    "SELECT import_id, severity, COUNT(*) AS count FROM events "
                    "WHERE event_type='alert' GROUP BY import_id, severity")]
            severity_by_import = {}
            for row in severity_rows:
                severity_by_import.setdefault(row['import_id'], []).append(row)
            run_rows = [
                (link(f"/alerts?import_id={run['id']}", run['original_name']) +
                 f'<br><small>Import ID: <code>{esc(run["id"])}</code></small>',
                 esc('PCAP' if run['kind'] == 'pcap' else 'EVE log'),
                 esc(run['status']), esc(run['event_count']),
                 link(f"/alerts?import_id={run['id']}", f"{run['alert_count']} alerts"),
                 esc(severity_breakdown(severity_by_import.get(run['id'], []))),
                 esc(run['sensor_elapsed_seconds'] if run['sensor_elapsed_seconds'] is not None
                     else run['elapsed_seconds']),
                 esc(run['sensor_peak_rss_kib'] if run['sensor_peak_rss_kib'] is not None
                     else run['peak_rss_kib']),
                 esc(run['started_at']), esc(run['error']))
                for run in runs
            ]
            form = (f'<div class="card"><h2>Import evidence</h2><p>Enter a file path on this machine. '
                    f'Relative paths start at <code>{esc(Path.cwd())}</code>. '
                    f'PCAP import runs Suricata and may take several minutes.</p>'
                    f'<form method="post" action="/imports"><input type="hidden" name="csrf" value="{csrf_token}">'
                    '<label for="kind">Source</label><select id="kind" name="kind"><option value="pcap">PCAP via Suricata</option>'
                    '<option value="eve">Existing EVE log</option></select>'
                    '<label for="path">File path</label><input id="path" name="path" required>'
                    '<label for="config">Suricata config path (PCAP)</label><input id="config" name="config" '
                    'placeholder="/etc/suricata/suricata.yaml">'
                    '<label for="rules">Exclusive rules file (PCAP, optional)</label><input id="rules" name="rules">'
                    '<button type="submit">Import</button></form></div>')
            body = form + '<div class="card"><h2>Recent imports</h2>'
            body += table(('Source', 'Type', 'Status', 'Events', 'Alerts', 'Suricata alert severities', 'Seconds',
                           'Peak RSS KiB', 'Imported', 'Error'), run_rows) if runs else '<p>No imports yet.</p>'
            body += '</div>'
            self.respond(200, 'Overview', body)

        def alerts(self):
            query = parse_qs(urlparse(self.path).query)
            selected = query.get('import_id', [None])[0]
            try:
                number = int(query.get('page', ['1'])[0])
            except ValueError as exc:
                raise ValueError('Invalid page number') from exc
            if number < 1:
                raise ValueError('Invalid page number')
            per_page = 100
            with EvidenceStore(data_dir / 'bluecheese.sqlite3') as store:
                imports = [dict(row) for row in store.db.execute(
                    "SELECT i.id, i.status, i.started_at, a.original_name, a.kind "
                    "FROM imports i JOIN artifacts a ON a.id=i.input_artifact_id "
                    "ORDER BY i.started_at DESC")]
                if selected is None:
                    selected = next((run['id'] for run in imports if run['status'] == 'complete'), 'all')
                if selected != 'all' and not any(run['id'] == selected for run in imports):
                    raise ValueError('Import not found')
                clause = " AND e.import_id=?" if selected != 'all' else ''
                parameters = (selected,) if selected != 'all' else ()
                total = store.db.execute(
                    "SELECT COUNT(*) FROM events e WHERE e.event_type='alert'" + clause,
                    parameters).fetchone()[0]
                severity_rows = [dict(row) for row in store.db.execute(
                    "SELECT e.severity, COUNT(*) AS count FROM events e "
                    "WHERE e.event_type='alert'" + clause + " GROUP BY e.severity",
                    parameters)]
                if number > max(1, (total + per_page - 1) // per_page):
                    raise ValueError('Page not found')
                alerts = [dict(row) for row in store.db.execute(
                    "SELECT e.id, e.timestamp, e.signature, e.severity, e.src_ip, e.dest_ip, "
                    "e.import_id, a.original_name, t.priority FROM events e "
                    "JOIN imports i ON i.id=e.import_id "
                    "JOIN artifacts a ON a.id=i.input_artifact_id "
                    "LEFT JOIN triage t ON t.event_id=e.id "
                    "WHERE e.event_type='alert'" + clause +
                    " ORDER BY e.timestamp DESC, e.id LIMIT ? OFFSET ?",
                    (*parameters, per_page, (number - 1) * per_page))]
            options = '<option value="all"' + (' selected' if selected == 'all' else '') + '>All imports</option>'
            for run in imports:
                options += (f'<option value="{esc(run["id"])}"' +
                            (' selected' if run['id'] == selected else '') +
                            f'>{esc(run["original_name"])} · {esc(run["started_at"])} · {esc(run["status"])}</option>')
            current = next((run for run in imports if run['id'] == selected), None)
            scope = (f"{current['original_name']} ({current['kind']}; {current['status']})"
                     if current else 'all imports')
            start = (number - 1) * per_page + 1 if alerts else 0
            end = (number - 1) * per_page + len(alerts)
            content = (f'<div class="card"><div class="actions"><form method="get" action="/alerts">'
                       f'<label for="import_id">Show alerts from</label><select id="import_id" name="import_id">{options}</select>'
                       f'<button type="submit">Show alerts</button></form>{link("/", "View imports")}</div>'
                       f'<p><b>{esc(total)} alerts</b> from {esc(scope)}. Showing {start}–{end}.</p>'
                       f'<p>Suricata alert severities: {esc(severity_breakdown(severity_rows))}.</p>'
                       '<p class="muted">Severity and triage priority apply to individual alerts. '
                       'This page does not determine whether the capture is malicious.</p>')
            rows = [(link(f"/alerts/{row['id']}", row['timestamp']),
                     link(f"/alerts?import_id={row['import_id']}", row['original_name']),
                     esc(row['signature']), esc(row['severity']),
                     esc(f"{row['src_ip']} → {row['dest_ip']}"),
                     esc(row['priority'] or 'untriaged')) for row in alerts]
            content += (table(('Time', 'Source', 'Detection', 'Suricata severity', 'Endpoints', 'Alert priority'), rows)
                        if rows else '<p>No alerts in this view.</p>')
            if total > per_page:
                content += '<nav class="pagination" aria-label="Alert pages">'
                if number > 1:
                    content += link('/alerts?' + urlencode({'import_id': selected, 'page': number - 1}), 'Previous')
                if end < total:
                    content += link('/alerts?' + urlencode({'import_id': selected, 'page': number + 1}), 'Next')
                content += '</nav>'
            content += '</div>'
            self.respond(200, 'Alerts', content)

        def alert_detail(self, event_id):
            event_id = self.valid_id(event_id)
            with EvidenceStore(data_dir / 'bluecheese.sqlite3') as store:
                alert = store.get_event(event_id)
                if alert is None or alert['event_type'] != 'alert':
                    raise ValueError('Alert not found')
                related = store.related_events(alert)
                triage = store.db.execute('SELECT * FROM triage WHERE event_id=?', (event_id,)).fetchone()
                source = store.db.execute(
                    "SELECT a.original_name, a.kind FROM imports i JOIN artifacts a "
                    "ON a.id=i.input_artifact_id WHERE i.id=?", (alert['import_id'],)).fetchone()
                severity_rows = [dict(row) for row in store.db.execute(
                    "SELECT severity, COUNT(*) AS count FROM events "
                    "WHERE import_id=? AND event_type='alert' GROUP BY severity",
                    (alert['import_id'],))]
            import_alerts_link = link(f"/alerts?import_id={alert['import_id']}",
                                      'All alerts from this import')
            body = (f'<div class="card"><h2>{esc(alert["signature"])}</h2>'
                    f'<p><b>Source:</b> {esc(source["original_name"])} ({esc(source["kind"])}) · '
                    f'{import_alerts_link}</p>'
                    f'<p><b>Time:</b> {esc(alert["timestamp"])}<br><b>Suricata severity for this alert:</b> {esc(alert["severity"])}'
                    f'<br><b>Network:</b> {esc(alert["src_ip"])}:{esc(alert["src_port"])} → '
                    f'{esc(alert["dest_ip"])}:{esc(alert["dest_port"])}</p>'
                    f'<p><b>All alerts from this import:</b> {esc(severity_breakdown(severity_rows))}.</p>'
                    f'<p>{link(f"/evidence/{event_id}", "Original alert record")}</p>'
                    f'<form method="post" action="/triage/{event_id}">'
                    f'<input type="hidden" name="csrf" value="{csrf_token}">'
                    '<button type="submit">Run triage</button></form></div>')
            if triage:
                body += (f'<div class="card"><h2>Alert triage</h2><p><span class="badge">{esc(triage["priority"])}</span> '
                         f'{esc(triage["disposition"])}</p><p>{esc(triage["rationale"])}</p>'
                         '<p class="muted">This priority applies to this alert only. '
                         'It is not a verdict on the entire capture.</p>'
                         f'<p>{link(f"/reports/{event_id}", "Open case report")}</p></div>')
            rows = [(esc(row['timestamp']), esc(row['event_type']),
                     link(f"/evidence/{row['id']}", row['id'])) for row in related]
            body += '<div class="card"><h2>Related observations</h2>'
            body += table(('Time', 'Type', 'Evidence'), rows) if rows else '<p>None in this import and time window.</p>'
            body += '</div>'
            self.respond(200, 'Alert', body)

        def evidence(self, event_id):
            event_id = self.valid_id(event_id)
            with EvidenceStore(data_dir / 'bluecheese.sqlite3') as store:
                item = store.resolve(event_id)
            body = (f'<div class="card"><p><b>Artifact:</b> {esc(item["artifact_id"])}'
                    f'<br><b>SHA-256:</b> {esc(item["sha256"])}'
                    f'<br><b>Line:</b> {esc(item["line_number"])}</p>'
                    f'<h2>Original record</h2><pre>{esc(item["original_record"])}</pre></div>'
                    f'<p>{link("/alerts", "All alerts")}</p>')
            self.respond(200, 'Evidence', body)

        def report(self, event_id):
            event_id = self.valid_id(event_id)
            report = case_report(data_dir, event_id)
            interpretation = report['interpretation']
            detection = report['detection']
            with EvidenceStore(data_dir / 'bluecheese.sqlite3') as store:
                source = store.db.execute(
                    "SELECT a.original_name FROM imports i JOIN artifacts a "
                    "ON a.id=i.input_artifact_id WHERE i.id=?",
                    (report['import']['id'],)).fetchone()
                severity_rows = [dict(row) for row in store.db.execute(
                    "SELECT severity, COUNT(*) AS count FROM events "
                    "WHERE import_id=? AND event_type='alert' GROUP BY severity",
                    (report['import']['id'],))]
            rows = [(esc(ref['event_id']), esc(ref['line_number']),
                     link(f"/evidence/{ref['event_id']}", 'View original'))
                    for ref in report['evidence']]
            import_alerts_link = link(f"/alerts?import_id={report['import']['id']}",
                                      'All alerts from this import')
            body = (f'<div class="card"><b>Source:</b> {esc(source["original_name"])} · '
                    f'{import_alerts_link}'
                    f'<p><b>All alerts from this import:</b> {esc(severity_breakdown(severity_rows))}.</p>'
                    '<p>This report evaluates one alert. Its priority is not a verdict on the entire capture.</p></div>'
                    f'<div class="grid"><div class="card"><h2>Detection</h2><p>{esc(detection["signature"])}</p>'
                    f'<p>Signature ID: {esc(detection["signature_id"])}</p></div>'
                    f'<div class="card"><h2>Alert triage</h2><p><span class="badge">{esc(interpretation["priority"])}</span> '
                    f'{esc(interpretation["disposition"])}</p><p>{esc(interpretation["rationale"])}</p></div></div>'
                    '<div class="card"><h2>Evidence references</h2>'
                    + table(('Event ID', 'Line', 'Original'), rows) + '</div>'
                    '<div class="card"><h2>Limitations</h2><ul>'
                    + ''.join(f'<li>{esc(item)}</li>' for item in interpretation['limitations']) + '</ul></div>'
                    '<div class="card"><h2>Import measurements</h2><pre>'
                    + esc(json.dumps(report['import'], indent=2)) + '</pre></div>')
            self.respond(200, 'Case report', body)

    return Handler


def serve(data_dir, port=8765):
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(data_dir, token))
    print(f'Blue Cheese UI: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
