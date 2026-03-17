# Portfolio Outlook Manager

Portfolio Outlook Manager is a lightweight FastAPI + Jinja application for day-to-day portfolio operations.

## Milestone 5 highlights
- Usability-focused owned portfolio table (search, sort, filter, incomplete-only view)
- Usability-focused watchlist table (search, sort, filter)
- Watchlist-to-owned promotion flow (identity preserved, lots still required for position math)
- Improved import feedback (clear totals + row-level errors)
- CSV export routes for portfolio, lots, and watchlist
- SQLite backup copy action from Status page
- Refined asset detail hierarchy and clearer empty/error states
- Compact operational status surface for scheduler + data completeness

## Requirements
- Python 3.11+
- SQLite (default)

## First-run setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # optional
python scripts/init_db.py
uvicorn app.main:app --reload
```

## Environment variables
- `DATABASE_URL` (default: `sqlite:///./portfolio.db`)
- `TWELVE_DATA_API_KEY` (optional, needed for Twelve Data quote/fx ingestion)
- `SCHEDULER_ENABLED` (`true` by default)

## Main workflows
- Dashboard: `GET /` (supports query-param search/filter/sort)
- Watchlist: `GET /watchlist` (supports query-param search/filter/sort)
- Import: `GET/POST /imports/csv`
- Export portfolio: `GET /exports/portfolio.csv`
- Export lots: `GET /exports/portfolio-lots.csv`
- Export watchlist: `GET /exports/watchlist.csv`
- Backup SQLite copy: `POST /exports/backup-db`
- Status + manual operations: `GET /status`

## CSV examples
Owned import columns:
`display_name,asset_type,quote_currency,exchange,isin,quantity,buy_price,buy_currency,buy_date,fees,notes`

Example:
```csv
display_name,asset_type,quote_currency,exchange,isin,quantity,buy_price,buy_currency,buy_date,fees,notes
Apple,stock,USD,NASDAQ,US0378331005,2,180,USD,2024-01-05,1.00,starter lot
```

Watchlist import columns:
`display_name,asset_type,quote_currency,exchange,isin,notes`

Example:
```csv
display_name,asset_type,quote_currency,exchange,isin,notes
iShares Core MSCI World,etf,EUR,XETRA,IE00B4L5Y983,long-term candidate
```

## Backup and restore
- Create backup copy in UI from `/status` (writes timestamped file under `./backups`).
- Restore manually by stopping app and replacing `portfolio.db` with selected backup file.

## Raspberry Pi deployment notes
1. Use Python 3.11 and a virtual environment.
2. Keep `SCHEDULER_ENABLED=true` only on one instance.
3. Prefer local SSD/fast SD and periodic backups (`/exports/backup-db`).
4. Run with `uvicorn` behind a lightweight reverse proxy.

## systemd service example
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
ExecStart=/home/pi/Portfolio-Outlook-Manager/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Tests
```bash
pytest
```
