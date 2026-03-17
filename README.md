# Portfolio Outlook Manager

Portfolio Outlook Manager is a FastAPI + Jinja application for portfolio operations with polling, outlook generation, evaluation, alerts, cleanup retention, and backup workflows.

## Implemented feature set
- Portfolio dashboard (owned + watchlist), lots, cash, term deposits.
- Provider abstraction (manual + Twelve Data fallback), backfill, and polling coordinator.
- Outlook engine, action layer, evaluation/calibration, refined ensemble outputs.
- Search/filter/sort/export across dashboard/watchlist.
- Alert rules + in-app alert events.
- Operational status page with runtime, data coverage, outlook quality, and manual operations.
- Retention cleanup service with safe pruning guardrails.
- SQLite backup workflow with latest backup metadata surfaced on `/status`.

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
```

## Run
```bash
uvicorn app.main:app --reload
```

## Test
```bash
pytest
```

## Environment variables
- `DATABASE_URL` (default `sqlite:///./portfolio.db`)
- `TWELVE_DATA_API_KEY` (optional)
- `SCHEDULER_ENABLED` (`true` default)
- `BACKUP_DIR` (`backups` default)
- `RETENTION_RAW_QUOTES_DAYS` (default `30`)
- `RETENTION_NORMALIZED_QUOTES_DAYS` (default `365`)
- `RETENTION_FX_DAYS` (default `365`)
- `RETENTION_OUTLOOK_SNAPSHOTS_DAYS` (default `365`)
- `RETENTION_ACTION_SNAPSHOTS_DAYS` (default `365`)
- `RETENTION_OUTLOOK_EVALUATIONS_DAYS` (default `730`)
- `RETENTION_ALERT_EVENTS_DAYS` (default `180`)

## First-run checklist
1. Initialize DB (`python scripts/init_db.py`).
2. Add assets and lots (or import CSV).
3. Backfill history per asset from asset detail page.
4. Open `/status` and run: polling, outlook, evaluation, alerts.
5. Verify data coverage (quote/FX) and incomplete valuation counts.

## Backup procedure
- UI route: `/status` → **Create backup**.
- API route: `POST /exports/backup-db`.
- Backups are timestamped SQLite files in `BACKUP_DIR`.
- `/status` shows latest backup timestamp and path.

## Restore procedure (manual, safe)
1. Stop the app/service.
2. Copy selected backup over active SQLite DB file.
3. Start app/service.
4. Check `/status` for scheduler and row-count sanity.

## Raspberry Pi deployment
See `docs/raspberry_pi_runbook.md` for a concise runbook.

### systemd example
```ini
[Unit]
Description=Portfolio Outlook Manager
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Portfolio-Outlook-Manager
Environment="DATABASE_URL=sqlite:////home/pi/Portfolio-Outlook-Manager/portfolio.db"
Environment="TWELVE_DATA_API_KEY=YOUR_KEY"
Environment="SCHEDULER_ENABLED=true"
Environment="BACKUP_DIR=/home/pi/Portfolio-Outlook-Manager/backups"
ExecStart=/home/pi/Portfolio-Outlook-Manager/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting
- **Missing quote**: confirm provider symbol/ISIN, run manual polling, and verify asset is not cash/term deposit.
- **Missing FX**: check quote currency vs base currency; run polling/backfill for FX-bearing assets.
- **Scheduler not running**: verify `SCHEDULER_ENABLED=true`, dependency install, and `/status` scheduler block.
- **Totals incomplete**: inspect missing quote/FX counts on `/status`, resolve data gaps, rerun outlook/evaluation.
