from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService
from app.services.dashboard_service import DashboardService


def test_dashboard_empty(db_session):
    svc = DashboardService(db_session)
    assert svc.owned_rows() == []
    assert svc.watchlist_rows() == []
    assert svc.summary_cards().total_invested == 0
    assert svc.summary_cards().totals_complete is True


def test_missing_fx_keeps_quote_value_but_base_none(db_session):
    instrument_service = InstrumentService(db_session)
    asset = instrument_service.create_asset(
        AssetCreate(display_name="USD Asset", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="USD")
    )
    LotService(db_session).create_lot(
        LotCreate(asset_id=asset.id, quantity="2", buy_price="10", buy_currency="USD", buy_date="2024-01-01", fees="0")
    )

    svc = DashboardService(db_session)
    rows = svc.owned_rows(quote_price_by_asset_id={asset.id: Decimal("12")}, fx_rate_by_currency={})
    row = rows[0]

    assert row.valuation.value_in_quote == Decimal("24")
    assert row.valuation.value_in_base is None
    assert row.valuation.unrealized_pl_base is None
    assert row.valuation.fx_status == "missing"
    assert row.valuation.valuation_warning == "FX conversion unavailable"


def test_summary_cards_flags_incomplete_when_fx_or_quote_missing(db_session):
    svc = InstrumentService(db_session)
    eur_asset = svc.create_asset(
        AssetCreate(display_name="EUR Asset", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR")
    )
    usd_asset = svc.create_asset(
        AssetCreate(display_name="USD Asset", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="USD")
    )
    lot_service = LotService(db_session)
    lot_service.create_lot(LotCreate(asset_id=eur_asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01", fees="0"))
    lot_service.create_lot(LotCreate(asset_id=usd_asset.id, quantity="1", buy_price="10", buy_currency="USD", buy_date="2024-01-01", fees="0"))

    dashboard = DashboardService(db_session)
    rows = dashboard.owned_rows(quote_price_by_asset_id={eur_asset.id: Decimal("12"), usd_asset.id: Decimal("15")}, fx_rate_by_currency={})
    summary = dashboard.summary_cards(rows)

    assert summary.totals_complete is False
    assert summary.missing_fx_asset_count == 1
    assert summary.missing_quote_asset_count == 0
    assert summary.total_current_value_base == Decimal("12")
