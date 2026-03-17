from datetime import date, datetime
from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.providers.types import NormalizedFXRate, NormalizedQuote
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.asset_detail_service import AssetDetailService
from app.services.history_service import HistoryService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService
from app.services.market_data_ingestion_service import MarketDataIngestionService


class FakeProvider:
    def fetch_historical_daily(self, asset, start_date, end_date):
        return [
            NormalizedQuote("fake", "ABC", Decimal("10.5"), asset.quote_currency, datetime(2024, 1, 2), "1day", {"c": "10.5"}),
            NormalizedQuote("fake", "ABC", Decimal("11.5"), asset.quote_currency, datetime(2024, 1, 3), "1day", {"c": "11.5"}),
        ]

    def fetch_historical_fx(self, base_currency, quote_currency, start_date, end_date):
        return [NormalizedFXRate("fake", base_currency, quote_currency, Decimal("0.9"), datetime(2024, 1, 2), "1day", {"c": "0.9"})]


def test_backfill_writes_raw_and_normalized_quotes_and_fx(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="A", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="USD", is_manual_asset=False))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="USD", buy_date="2024-01-01"))

    svc = HistoryService(db_session)
    svc.provider = FakeProvider()
    result = svc.backfill_asset(asset)

    assert result["ok"] is True
    assert len(asset.market_quotes) == 2
    assert len(asset.market_quotes_raw) == 2


def test_repeated_backfill_dedupes(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="A2", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False))
    svc = HistoryService(db_session)
    svc.provider = FakeProvider()
    svc.backfill_asset(asset)
    svc.backfill_asset(asset)
    db_session.refresh(asset)
    assert len(asset.market_quotes) == 2


def test_freshness_from_real_timestamp(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Fresh", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False))
    row = MarketDataIngestionService(db_session).ingest_quote(
        asset.id,
        NormalizedQuote("fake", "X", Decimal("1"), "EUR", datetime.utcnow(), "spot", {}),
        is_backfill=False,
    )
    assert row.freshness_status in {"fresh", "delayed"}


def test_asset_detail_exposes_recent_history(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="A3", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", is_manual_asset=False))
    ingest = MarketDataIngestionService(db_session)
    ingest.ingest_quote(asset.id, NormalizedQuote("fake", "A3", Decimal("1"), "EUR", datetime(2024, 1, 1), "1day", {}), False)
    db_session.commit()
    model = AssetDetailService(db_session).build(asset.id)
    assert len(model["recent_quotes"]) == 1
