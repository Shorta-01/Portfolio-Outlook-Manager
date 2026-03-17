from decimal import Decimal
from app.models.asset import AssetMode, AssetType
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.schemas.asset import AssetCreate
from app.services.instrument_service import InstrumentService


def test_cash_asset_never_creates_polling_rule(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR"))
    assert PollingRuleRepository(db_session).count() == 0


def test_term_deposit_never_creates_polling_rule(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="td", asset_type=AssetType.TERM_DEPOSIT, asset_mode=AssetMode.TERM_DEPOSIT, quote_currency="EUR"))
    assert PollingRuleRepository(db_session).count() == 0


def test_poll_capable_owned_and_watchlist_create_one_rule_only(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="owned", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    svc.create_asset(AssetCreate(display_name="watch", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    assert PollingRuleRepository(db_session).count() == 2


def test_reusing_identity_does_not_create_duplicate_polling_rule(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="same", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    svc.create_asset(AssetCreate(display_name="same", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    assert PollingRuleRepository(db_session).count() == 1


def test_term_deposit_rate_over_one_is_normalized_from_percent(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(
            display_name="td-normalized",
            asset_type=AssetType.TERM_DEPOSIT,
            asset_mode=AssetMode.TERM_DEPOSIT,
            quote_currency="EUR",
            term_deposit_rate=Decimal("3.5"),
        )
    )
    assert asset.term_deposit_rate == Decimal("0.035")


def test_term_deposit_rate_zero_to_one_is_stored_as_decimal_fraction(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(
            display_name="td-decimal",
            asset_type=AssetType.TERM_DEPOSIT,
            asset_mode=AssetMode.TERM_DEPOSIT,
            quote_currency="EUR",
            term_deposit_rate=Decimal("0.035"),
        )
    )
    assert asset.term_deposit_rate == Decimal("0.035")