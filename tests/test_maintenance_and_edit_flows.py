from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.asset import AssetMode, AssetType
from app.models.market_quote import MarketQuote
from app.schemas.asset import AssetCreate, AssetUpdate
from app.schemas.lot import LotCreate, LotUpdate
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService
from app.services.maintenance_service import MaintenanceService


def test_asset_edit_cash_and_term_deposit(db_session):
    cash = InstrumentService(db_session).create_asset(AssetCreate(display_name="Cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR", current_amount="10"))
    updated_cash = InstrumentService(db_session).update_asset(cash.id, AssetUpdate(display_name="Cash Box", quote_currency="eur", current_amount="20"))
    assert updated_cash.display_name == "Cash Box"
    assert updated_cash.current_amount == Decimal("20")

    td = InstrumentService(db_session).create_asset(
        AssetCreate(
            display_name="TD",
            asset_type=AssetType.TERM_DEPOSIT,
            asset_mode=AssetMode.TERM_DEPOSIT,
            quote_currency="EUR",
            principal_amount="1000",
            interest_rate_annual="0.05",
            start_date="2024-01-01",
            maturity_date="2025-01-01",
        )
    )
    updated_td = InstrumentService(db_session).update_asset(
        td.id,
        AssetUpdate(
            display_name="TD2",
            quote_currency="EUR",
            principal_amount="1200",
            interest_rate_annual="5",
            start_date="2024-01-01",
            maturity_date="2025-01-01",
            bank_name="Bank",
        ),
    )
    assert updated_td.principal_amount == Decimal("1200")
    assert updated_td.interest_rate_annual == Decimal("0.05")


def test_lot_edit_and_delete(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="A", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    lot = LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    updated = LotService(db_session).update_lot(lot.id, LotUpdate(quantity="2", buy_price="12", buy_currency="usd", buy_date="2024-01-02", fees="1", notes="n"))
    assert updated.quantity == Decimal("2")
    assert updated.buy_currency == "USD"

    asset_id = LotService(db_session).delete_lot(lot.id)
    assert asset_id == asset.id
    assert LotService(db_session).list_lots_for_asset(asset.id) == []


def test_archive_and_safe_delete_policy(db_session):
    owned = InstrumentService(db_session).create_asset(AssetCreate(display_name="Owned", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    watch = InstrumentService(db_session).create_asset(AssetCreate(display_name="Watch", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    InstrumentService(db_session).archive_asset(owned.id)
    assert InstrumentService(db_session).asset_repo.get(owned.id).enabled is False

    InstrumentService(db_session).delete_asset_if_safe(watch.id)
    assert InstrumentService(db_session).asset_repo.get(watch.id) is None

    with pytest.raises(ValueError):
        InstrumentService(db_session).delete_asset_if_safe(owned.id)


def test_maintenance_issue_detection_and_duplicates(db_session):
    a1 = InstrumentService(db_session).create_asset(AssetCreate(display_name="Dup", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR", isin="X1"))
    a2 = InstrumentService(db_session).create_asset(AssetCreate(display_name="Dup", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", isin="X1"))
    a1.created_at_utc = datetime.utcnow() - timedelta(days=8)
    a2.created_at_utc = datetime.utcnow() - timedelta(days=20)
    db_session.add(MarketQuote(asset_id=a2.id, provider_name="seed", price=Decimal("1"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow() - timedelta(days=15), freshness_status="stale", interval_type="spot", is_backfill=False))
    db_session.commit()

    report = MaintenanceService(db_session).scan()
    labels = [i.label for i in report["issues"]]
    assert "Owned asset has no lots" in labels
    assert "Stale watchlist quote" in labels
    assert "Duplicate-like ISIN" in labels
    assert report["issue_count"] >= 3
