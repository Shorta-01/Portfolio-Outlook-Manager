# Portfolio Outlook Manager

Portfolio Outlook Manager is a FastAPI + Jinja application for owned portfolio and watchlist tracking with deterministic asset identity, lot-based valuation, manual quote/FX management, and now a first market-data ingestion lifecycle.

## Current implemented scope (through Milestone 3)
- FastAPI + Jinja server-rendered app
- SQLite + SQLAlchemy 2.x persistence
- Owned dashboard + watchlist
- Lot-based aggregation and valuation
- CSV import for owned/watchlist assets
- Deterministic asset identity reuse
- Cash + term-deposit valuation support
- Manual quote and FX entry flows
- Status page trust and completeness signals
- Provider abstraction and symbol resolution
- Historical backfill (daily) for market-priced assets
- Unified ingestion path for raw + normalized quotes and FX rows
- APScheduler polling coordinator (central run, every minute)
- Asset-detail recent stored quote history
- Status metadata for scheduler/history coverage

## Milestone 3 setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # optional if you keep env vars in a file
```

Environment variables (optional):
- `DATABASE_URL` (default `sqlite:///./portfolio.db`)
- `TWELVE_DATA_API_KEY` (required for Twelve Data external ingestion)
- `SCHEDULER_ENABLED` (`true` by default)

## Initialize DB
```bash
python scripts/init_db.py
```

## Run dev server
```bash
uvicorn app.main:app --reload
```

## Milestone 3 operational flows
- Backfill one asset: `POST /assets/{asset_id}/backfill`
- Run one polling cycle manually: `POST /admin/polling/run-once`
- View scheduler/history metadata: `GET /status`

## Run tests
```bash
pytest
```

## CSV formats
Owned lots CSV columns:
`display_name,asset_type,quote_currency,exchange,isin,quantity,buy_price,buy_currency,buy_date,fees,notes`

Watchlist CSV columns:
`display_name,asset_type,quote_currency,exchange,isin,notes`
