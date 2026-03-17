# Raspberry Pi deployment runbook

## Install
1. Install Python 3.11, git, and sqlite packages.
2. Clone repo, create virtualenv, install requirements.
3. Set env vars (`DATABASE_URL`, `TWELVE_DATA_API_KEY`, `SCHEDULER_ENABLED`, retention vars).

## systemd
Use the `portfolio-outlook-manager.service` example in README and ensure:
- only one instance has `SCHEDULER_ENABLED=true`
- `WorkingDirectory` points to repo
- backup directory exists and has write permissions

## First run
1. `python scripts/init_db.py`
2. Start app
3. Add assets / lots or import CSV
4. Backfill owned/watchlist assets
5. Run manual polling/outlook/evaluation/alerts once from `/status`
6. Open `/maintenance` and resolve duplicate-like, unresolved lookup, or stale/incomplete issues
7. Verify `/status` has quote/FX coverage and no unresolved missing counts

## Ongoing maintenance safety
- Use asset detail pages to edit assets/lots.
- Prefer **archive** over hard delete.
- Hard delete is intended only for dependency-free watchlist rows and confirmed lot deletes.
- Run a backup from `/status` before destructive changes.

## Restore
1. Stop service: `sudo systemctl stop portfolio-outlook-manager`
2. Copy backup file over DB file.
3. Start service: `sudo systemctl start portfolio-outlook-manager`
4. Open `/status` and verify row counts / scheduler state.
