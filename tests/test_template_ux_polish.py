from datetime import datetime
from decimal import Decimal

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.models.asset import AssetMode, AssetType
from app.models.market_quote import MarketQuote
from app.routes.dashboard import _ui_context
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.dashboard_service import DashboardService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


templates = Jinja2Templates(directory="app/templates")


def _render(template_name: str, **context) -> str:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    response = templates.TemplateResponse(template_name, {"request": request, **context})
    return response.body.decode()


def test_dashboard_empty_state_hides_filters_and_shows_actions(db_session):
    service = DashboardService(db_session)
    query = {"q": "", "sort": "asset_name", "dir": "asc", "asset_type": "", "currency": "", "outlook": "", "action": "", "freshness": "", "source": "", "incomplete_only": "0"}
    rows = service.query_owned_rows(query)
    html = _render("dashboard.html", rows=rows, summary=service.summary_cards(), message=None, message_level="notice", **_ui_context(service.owned_rows(), query))

    assert 'class="filters"' not in html
    assert "Your portfolio is empty" in html
    assert "/assets/new" in html
    assert "/imports/csv" in html


def test_watchlist_empty_state_hides_filters_and_shows_actions(db_session):
    service = DashboardService(db_session)
    query = {"q": "", "sort": "display_name", "dir": "asc", "asset_type": "", "currency": "", "outlook": "", "action": "", "freshness": "", "source": ""}
    rows = service.query_watchlist_rows(query)
    html = _render("watchlist.html", rows=rows, message=None, message_level="notice", **_ui_context(service.watchlist_rows(), query))

    assert 'class="filters"' not in html
    assert "Your watchlist is empty" in html
    assert "/assets/new" in html
    assert "/imports/csv" in html


def test_dashboard_non_empty_shows_filters_and_search(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Alpha", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    db_session.add(MarketQuote(asset_id=asset.id, provider_name="seed", price=Decimal("11"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow(), freshness_status="fresh", interval_type="spot", is_backfill=False))
    db_session.commit()

    service = DashboardService(db_session)
    query = {"q": "", "sort": "asset_name", "dir": "asc", "asset_type": "", "currency": "", "outlook": "", "action": "", "freshness": "", "source": "", "incomplete_only": "0"}
    rows = service.query_owned_rows(query)
    html = _render("dashboard.html", rows=rows, summary=service.summary_cards(), message=None, message_level="notice", **_ui_context(service.owned_rows(), query))

    assert 'class="filters"' in html
    assert 'name="q"' in html


def test_tooltips_present_in_key_templates():
    files = [
        "app/templates/components/summary_cards.html",
        "app/templates/components/portfolio_grid.html",
        "app/templates/components/watchlist_grid.html",
        "app/templates/asset_detail.html",
        "app/templates/status.html",
        "app/templates/alerts.html",
        "app/templates/alert_rules.html",
        "app/templates/import_csv.html",
        "app/templates/settings.html",
    ]
    for file_path in files:
        text = open(file_path, "r", encoding="utf-8").read()
        assert "data-tooltip" in text
