# Portfolio Outlook Manager

Portfolio Outlook Manager is a Python-first portfolio-aware decision platform. Milestone 1 provides foundational data model, routing, and server-rendered UI shells for owned positions and watchlist.

## Milestone 1 scope
- FastAPI + Jinja app shell
- SQLite + SQLAlchemy 2.x models
- Owned portfolio aggregation by asset (lot-based)
- Separate watchlist
- Asset and lot creation
- CSV import for owned/watchlist flows
- Settings, status, and health pages

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Initialize DB
```bash
python scripts/init_db.py
```

## Run dev server
```bash
uvicorn app.main:app --reload
```

## Run tests
```bash
pytest
```

## CSV formats
Owned lots CSV columns:
`display_name,asset_type,quote_currency,exchange,isin,quantity,buy_price,buy_currency,buy_date,fees,notes`

Watchlist CSV columns:
`display_name,asset_type,quote_currency,exchange,isin,notes`
