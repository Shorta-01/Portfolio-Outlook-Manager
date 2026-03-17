from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.models.fx_rate import FXRate
from app.models.market_quote import MarketQuote
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.schemas.quote_fx import FXRateCreate, MarketQuoteCreate
from app.services.dashboard_service import DashboardService
from app.services.fx_service import FXService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService
from app.services.market_data_admin_service import MarketDataAdminService
from app.services.valuation_service import ValuationService
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository


def test_market_asset_valuation_and_pl(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="ACME", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="USD"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="2", buy_price="100", buy_currency="USD", buy_date="2024-01-01", fees="10"))
    db_session.add(MarketQuote(asset_id=asset.id, provider_name="manual", price=Decimal("120"), quote_currency="USD", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.add(FXRate(pair_code="USD/EUR", base_currency="USD", quote_currency="EUR", rate=Decimal("0.9"), provider_name="manual", provider_timestamp_utc=datetime.utcnow(), interval_type="spot"))
    db_session.commit()

    row = ValuationService(LotRepository(db_session), MarketQuoteRepository(db_session), FXRateRepository(db_session)).aggregate_owned_asset(asset, "EUR")
    assert row.value_now == Decimal("216")
    assert row.unrealized_pl_amount == Decimal("6")
    assert row.unrealized_pl_percent == Decimal("2.857142857142857142857142857")


def test_fx_convert_same_currency_and_missing_rate(db_session):
    fx = FXService(FXRateRepository(db_session))
    assert fx.convert(Decimal("10"), "EUR", "EUR") == Decimal("10")
    assert fx.convert(Decimal("10"), "USD", "EUR") is None


def test_cash_and_term_deposit_valuation(db_session):
    cash = InstrumentService(db_session).create_asset(AssetCreate(display_name="Cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR", current_amount="1000"))
    td = InstrumentService(db_session).create_asset(
        AssetCreate(
            display_name="TD",
            asset_type=AssetType.TERM_DEPOSIT,
            asset_mode=AssetMode.TERM_DEPOSIT,
            quote_currency="EUR",
            principal_amount="1000",
            interest_rate_annual="0.10",
            start_date=date.today() - timedelta(days=30),
            maturity_date=date.today() + timedelta(days=30),
        )
    )

    svc = ValuationService(LotRepository(db_session), MarketQuoteRepository(db_session), FXRateRepository(db_session))
    cash_val = svc.value_for_asset(cash, Decimal("0"), Decimal("1000"), "EUR")
    td_val = svc.value_for_asset(td, Decimal("0"), Decimal("1000"), "EUR")
    assert cash_val.value_now_base_currency == Decimal("1000")
    assert td_val.value_now_base_currency > Decimal("1000")
    assert svc.maturity_value(td) >= td_val.value_now_base_currency


def test_freshness_mapping_and_source(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="A", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    old = datetime.utcnow() - timedelta(days=3)
    db_session.add(MarketQuote(asset_id=asset.id, provider_name="seed", price=Decimal("12"), quote_currency="EUR", provider_timestamp_utc=old, freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.commit()

    row = ValuationService(LotRepository(db_session), MarketQuoteRepository(db_session), FXRateRepository(db_session)).aggregate_owned_asset(asset, "EUR")
    assert row.freshness_status == "stale"
    assert row.source_label == "seed"


def test_dashboard_summary_totals(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="B", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="2", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    db_session.add(MarketQuote(asset_id=asset.id, provider_name="seed", price=Decimal("11"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.commit()

    summary = DashboardService(db_session).summary_cards()
    assert summary.total_invested == Decimal("20")
    assert summary.total_current_value == Decimal("22")


def test_manual_quote_fx_service_create(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="C", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="USD"))
    svc = MarketDataAdminService(db_session)
    q = svc.create_quote(MarketQuoteCreate(asset_id=asset.id, provider_name="manual", provider_symbol="C", price="10", quote_currency="USD", provider_timestamp_utc=datetime.utcnow()))
    fx = svc.create_fx_rate(FXRateCreate(base_currency="USD", quote_currency="EUR", rate="0.8", provider_name="manual", provider_timestamp_utc=datetime.utcnow()))
    assert q.id is not None
    assert fx.pair_code == "USD/EUR"
