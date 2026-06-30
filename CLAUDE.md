# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Web-based academic monitoring for **Siakang Untirta**: a FastAPI backend + Vue 3 frontend that periodically scrapes the campus portal (behind Cloudflare) and pushes grade / KRS-availability changes to Telegram & WhatsApp (WAHA).

## Commands

### Backend (Python, managed with `uv`)
- Install deps: `uv sync`
- Install browser (once): `uv run playwright install chromium`
- Run API (dev): `uv run uvicorn server.main:app --reload --port 8000`
- All tests: `uv run pytest`
- Single test: `uv run pytest tests/test_worker.py::TestNotifier::test_send_dispatches_to_both_channels`
- Filter by keyword: `uv run pytest -k waha`
- Ad-hoc unused-code check (no linter is configured): `uvx pyflakes worker server scraper_lib.py main.py`

### Frontend (`frontend/`, pnpm)
- `pnpm install`, dev server `pnpm run dev`, production build `pnpm run build`

### Full stack (Docker)
- `docker compose up -d --build` (frontend :3000, backend :8000 by default; override via `FRONTEND_PORT` / `BACKEND_PORT`)

### Running a worker by hand (to debug the scraper)
The worker takes ALL config from env vars (see Subprocess contract). Single pass then exit:
`MONITOR_TYPE=nilai LOGIN_ID=... PASSWORD=... FILE_DATA=/tmp/x.json INTERVAL=300 uv run python main.py --run-once`

## Architecture (the parts that span multiple files)

### Two-process model — the core idea
`server/` (FastAPI) does NOT scrape. It is a control plane: it CRUDs monitoring "tasks" in SQLite and launches/kills **one OS subprocess per running task**. Each subprocess is `python main.py` (the worker). Server and worker share NO in-process state — the ONLY server→worker channel is **environment variables** injected at spawn time in `server/manager.py:start_process`. So adding a worker setting means three coordinated edits: (1) store it on the task row, (2) inject it as an env var in `manager.py`, (3) read it in `worker/config.py`.

### Worker (`main.py` -> `worker/` package)
`main.py` is a thin entrypoint kept ONLY so the subprocess path (`SCRIPT_PATH` in `manager.py`) stays valid — do not move/rename it; put logic in `worker/`. Flow: `worker/runner.py:build_monitor()` reads `MONITOR_TYPE` and returns `GradeMonitor` (`monitors/nilai.py`) or `KrsMonitor` (`monitors/krs.py`), both subclassing `monitors/base.py:BaseMonitor` (login -> select semester -> mode-specific loop). `worker/config.py` exposes a module-level `config` singleton built from env **at import time** — env must be set before importing worker modules (true in the subprocess; in tests use `monkeypatch` on `runner.config`). `worker/notifications.py:Notifier` fans out to Telegram + WAHA. Console output goes through `worker/logging_setup.py:log()` (do not reintroduce a `print` override).

### Cloudflare-aware scraping (`scraper_lib.py`)
Plain HTTP cannot log in (Cloudflare JS challenge), so `BrowserSession` drives a real Playwright Chromium while exposing a `requests.Session`-like API (`.get` / `.post` / `.headers`) so the monitors read like HTTP code. It MUST launch with `channel="chromium"` — the old headless-shell is rejected by Cloudflare; do not switch. `.post()` runs `fetch()` inside the page (same-origin) to carry cookies through Cloudflare, which the KRS Livewire requests depend on. `SiakangScraper` is the variant the API uses for `/check-semesters` and login validation.

### Change detection & persisted state
Each worker writes its latest scrape to `FILE_DATA` (`data/value/last_values_{id}.json`) and diffs the next scrape against it to decide what to notify (new/changed grades, IPS/IPK changes, "all grades out", or newly-available KRS courses). Logs: `data/logs/task_{id}.log`; tasks DB: `data/db/tasks.db`. Tasks marked `running` are relaunched on server startup via `server/main.py` lifespan -> `manager.restore_running_tasks()`.

### Subprocess contract (env vars manager -> worker)
Per-task: `LOGIN_ID`, `PASSWORD`, `MONITOR_TYPE` (`nilai`|`krs`), `TARGET_COURSES` (JSON array, KRS only), `TARGET_SEMESTER_CODE`, `INTERVAL` (seconds), `CHAT_ID`, `WHATSAPP_NUMBER`, `WAHA_API_KEY`, `FILE_DATA`. Global notifier credentials (`TELEGRAM_TOKEN`, `WAHA_BASE_URL`, ...) come from the server's own `.env`. The worker honors `--run-once` for a single iteration (used by the API "refresh" endpoint via `manager.run_process_once`).

### Frontend
Standalone Vue 3 + Vite + Tailwind SPA (`frontend/`), axios -> backend REST, shadcn-vue/radix components. Shipped as a static nginx image; decoupled from backend internals beyond the API surface.

## Deployment notes
- Backend image runs **non-root (UID 1000)**. `docker-entrypoint.sh` starts as root only to `chown /app/data` (bind-mount self-heal for fresh deploys) then drops to `app` via `gosu`. Host `./data/*` files are therefore owned by UID 1000.
- Playwright browsers live at `/ms-playwright`; each active task launches its own Chromium (~150-300MB RAM) — mind capacity with many tasks.
- Dashboard access is gated by a 4-digit `APP_PIN`. CORS is controlled by `CORS_ORIGINS` (`*` allows all but disables credentials).
