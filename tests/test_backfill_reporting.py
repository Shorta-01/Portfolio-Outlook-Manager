import logging
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.db.base import Base
from app.dependencies import get_db_session
from app.main import app
from app.models.asset import AssetMode, AssetType
from app.providers.types import NormalizedQuote
from app.schemas.asset import AssetCreate
from app.services.history_service import HistoryService
from app.services.instrument_service import InstrumentService


class EmptyProvider:
    def fetch_historical_daily(self, asset, start_date, end_date):
        return []

    def fetch_historical_fx(self, base_currency, quote_currency, start_date, end_date):
        return []


class RowsProvider:
    def fetch_historical_daily(self, asset, start_date, end_date):
        return [NormalizedQuote("fake", "ABC", Decimal("10.5"), asset.quote_currency, datetime(2024, 1, 2), "1day", {})]

    def fetch_historical_fx(self, base_currency, quote_currency, start_date, end_date):
        return []


class ErrorProvider:
    def fetch_historical_daily(self, asset, start_date, end_date):
        raise RuntimeError("provider boom")

    def fetch_historical_fx(self, base_currency, quote_currency, start_date, end_date):
        return []


def test_backfill_result_non_market_priced_asset(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(display_name="Cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR", is_manual_asset=True, current_amount="100")
    )
    result = HistoryService(db_session).backfill_asset(asset)
    assert result["outcome"] == "skipped_not_market_priced"
    assert result["user_message"] == "Backfill skipped: asset is not market-priced."


def test_backfill_result_lookup_impossible(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(display_name="Manual", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=True)
    )
    svc = HistoryService(db_session)
    result = svc.backfill_asset(asset)
    assert result["outcome"] == "skipped_lookup_impossible"
    assert result["lookup_possible"] is False


def test_backfill_result_provider_not_configured(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(display_name="Fund", asset_type=AssetType.FUND, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False, isin="LU1234567890")
    )
    result = HistoryService(db_session).backfill_asset(asset)
    assert result["outcome"] == "failed_provider_not_configured"
    assert result["error_type"] == "provider_not_configured"


def test_backfill_result_no_rows(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(display_name="Stock", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False)
    )
    svc = HistoryService(db_session)
    svc.provider = EmptyProvider()
    result = svc.backfill_asset(asset)
    assert result["success"] is True
    assert result["outcome"] == "completed_no_data"
    assert result["rows_inserted_quotes"] == 0


def test_backfill_result_rows_inserted_and_logging(db_session, caplog):
    caplog.set_level(logging.INFO)
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(display_name="Stock", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False)
    )
    svc = HistoryService(db_session)
    svc.provider = RowsProvider()
    result = svc.backfill_asset(asset)
    assert result["success"] is True
    assert result["outcome"] == "completed_with_data"
    assert result["rows_inserted_quotes"] == 1
    assert "Backfill requested" in caplog.text
    assert "Backfill final outcome" in caplog.text


def test_backfill_provider_error_result(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(display_name="Stock", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False)
    )
    svc = HistoryService(db_session)
    svc.provider = ErrorProvider()
    result = svc.backfill_asset(asset)
    assert result["outcome"] == "failed_provider_error"
    assert result["user_message"] == "Backfill failed: provider returned error."


def test_backfill_route_uses_user_message_in_redirect():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def _override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_db
    try:
        with Session(engine) as session:
            asset = InstrumentService(session).create_asset(
                AssetCreate(display_name="Fund", asset_type=AssetType.FUND, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False, isin="LU1234567890")
            )
            asset_id = asset.id
        client = TestClient(app)
        response = client.post(f"/assets/{asset_id}/backfill", follow_redirects=False)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 303
    location = response.headers["location"]
    assert "Backfill+failed%3A+market+data+provider+is+not+configured." in location
    assert "message_level=warning" in location
