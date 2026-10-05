# Blue Cheese evidence and triage demo

This is a single-machine, offline Suricata evidence pipeline. It imports a PCAP through a local Suricata executable, or imports an existing Suricata `eve.json` file. It preserves the original input, indexes normalized events, and produces a deterministic triage report with resolvable evidence references. The triage role is rule-based and does not claim to determine malicious intent.

## Run the real Suricata demo

From the repository root, with Python 3.11 or later and Suricata on `PATH`:

```bash
./install-command.sh
bluecheese --data-dir ./demo-data import-pcap tests/fixtures/bluecheese-demo.pcap --config tests/fixtures/suricata-demo.yaml --rules tests/fixtures/bluecheese-demo.rules
bluecheese --data-dir ./demo-data alerts
ALERT_ID=$(bluecheese --data-dir ./demo-data alerts | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
bluecheese --data-dir ./demo-data triage "$ALERT_ID"
bluecheese --data-dir ./demo-data evidence "$ALERT_ID"
bluecheese --data-dir ./demo-data report "$ALERT_ID"
```

The installer links the repository's `./bluecheese` launcher into `~/.local/bin`, which is already on this machine's PATH. You can also run `./bluecheese` directly without installing the link. Keep the repository at this path while using the link.

The bundled PCAP has one UDP packet with the text `BLUECHEESE-DEMO`. The bundled rule detects that payload. The real Suricata run produces one alert and a related flow. The triage result is `low` priority and `needs_review`; it cites the two records and explains that a signature match does not prove compromise. Import the same PCAP twice to demonstrate idempotence: the import ID and event count stay the same. The local demo configuration avoids relying on a system Suricata config or ruleset.

To demonstrate log-only import without running the sensor, use `bluecheese --data-dir ./eve-data import-eve tests/fixtures/sample_eve.json`.

## Local web interface

```bash
bluecheese --data-dir ./demo-data serve
```

Open `http://127.0.0.1:8765/`. The page displays the evidence directory it is reading. Start the server with the same `--data-dir` used for CLI imports; refreshing the page shows new imports without restarting the server. Overview lists each input filename, import ID, status, event count, alert count, and Suricata severity breakdown. Select an import to see its alerts. After importing from the web form, the browser opens that import's alerts automatically. The Alerts page defaults to the latest completed import, supports selecting any import or all imports, and shows the source filename for each alert. Alert details link back to their source import and to the original record. Severity and triage priority apply to individual alerts; the application does not make a maliciousness verdict for an entire capture.

For the bundled PCAP, enter `tests/fixtures/bluecheese-demo.pcap` with config `tests/fixtures/suricata-demo.yaml` and rules `tests/fixtures/bluecheese-demo.rules`.

The server listens on localhost by default. Use `--port` to change its port. Imports run while the form request is open, so a large PCAP can leave the browser waiting; the import result remains in the evidence store after completion.

## Import a real PCAP

Use your normal Suricata configuration and ruleset:

```bash
bluecheese --data-dir ./real-data import-pcap /path/to/capture.pcap --config /path/to/suricata.yaml
```

Use `--suricata /path/to/suricata` if it is not on `PATH`. Use `--rules /path/to/rules.rules` to load a specific rules file exclusively. The adapter invokes Suricata offline with `-r` and imports its `eve.json`. If Suricata fails or produces no EVE file, the import is marked incomplete and the command exits with an error. A PCAP with no rule matches can still produce non-alert events; `alerts` will then be empty.

Run `python -m pytest -q` to check import, repeat import, raw evidence resolution, quarantine, triage, report, the web handlers, and the PCAP path with the installed Suricata executable. The real integration test skips only when Suricata is absent. This workspace blocks localhost sockets, so web tests exercise the request handlers directly rather than opening a listening port.

## Evidence and measurements

`demo-data/artifacts/` contains content-addressed copies of original inputs and EVE logs. `demo-data/bluecheese.sqlite3` contains artifacts, import runs, normalized events, import errors, and triage results. Each event stores an artifact ID and line number. `evidence <event-id>` retrieves the original line from the preserved file. SHA-256 hashes in the report identify the source artifact.

The import result records event and alert counts, invalid records, parsing time, peak Python process RSS in KiB, and total evidence-directory bytes at the end of the command. PCAP imports also record Suricata elapsed time and peak child-process RSS in KiB. Peak RSS is a process high-water mark, not a continuously sampled memory profile. Times are measured on this machine; they are not Security Onion comparison benchmarks.

Malformed EVE lines are kept in `import_errors`; the valid lines remain searchable and the import status becomes `incomplete`. Related-event retrieval is limited to the same import, a 15-minute window, and 20 rows. The current implementation indexes Suricata EVE only. Zeek correlation, DuckDB analytics, model-driven investigation, and persistent job recovery are later milestones.
