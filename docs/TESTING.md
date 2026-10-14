# Verification scope

```bash
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/python -m pip check
cd frontend
npm ci
npm run build
npx playwright install chromium
npm test
```

Python checks cover CLI/PCAP/SQLite behavior, evidence normalization and integrity,
ingestion, source continuity, single-writer ownership, snapshots, provider budgets,
retrieval-bound citations, reporting, backup/restore, and the production analyst
API. Tests use temporary state, offline fixtures, mocked models, deterministic
polling, and synchronization events. Local socket tests require socket permission.

Browser checks start the ordinary packaged server with a temporary state directory
and import an example through its normal API. They exercise the real alert-to-case
journey, evidence, activity, decisions, chat, exports, revisions, source controls,
theme persistence, and narrow navigation. A test-only response override stresses
long labels, IPv6, and literal HTML; it adds no application routes or modes.

Both themes are checked at 390, 768, 1280, and 1440 CSS pixels. Fourteen reviewed macOS
screenshots cover queues and case layouts. Axe checks cover page, drawer, tooltip,
chart, and chat states. Additional calculations check text, button, status, chart,
and control contrast. Reduced-motion and a 720px viewport equivalent to a 1440px
window at 200% zoom are exercised. Screenshot baselines are platform-specific;
review rendered changes before using `npm run test:update` on another platform.

The production build checks TypeScript and a 200 KiB gzip initial-JavaScript
budget. Native and Docker use the same runtime lockfile. A fresh temporary virtual
environment installs the wheel and verifies packaged assets, API startup, health,
empty initial state, and dependency consistency without Streamlit.

These checks do not establish screen-reader certification, cross-browser parity,
semantic model correctness, detection accuracy, sustained ingestion capacity, or
Docker execution. The Docker daemon is unavailable; Compose configuration validates.

The analyst accuracy suite uses reviewed synthetic facts, including deliberately
incorrect assertions attached to valid citations. It covers targeted retrieval,
UTC projection, immutable evidence, source-specific gaps, schema independence,
failed-request diagnostics and constrained conversational reading. See
[the workflow verification](ANALYST_WORKFLOW_VERIFICATION.md) for what these checks
establish and what still requires semantic review.

Measured on macOS/Python 3.13: 224 Python tests and 18 Chromium tests passed.
TypeScript, Ruff, Prettier and dependency checks passed; initial JavaScript is
101.0 KiB gzip. Live-provider results and their limits are recorded in
[session status](SESSION_STATUS.md).

Host-scope regressions use synthetic evidence to check scope isolation, diverse
retrieval before limits, cross-destination context delivery and bounded factual
correction with independent review. The ordinary API/browser journey verifies
starting a host case and preserving its scope across revisions.
