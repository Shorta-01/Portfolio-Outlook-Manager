from app.models.asset import AssetMode, AssetType
from decimal import Decimal
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.schemas.asset import AssetCreate
from app.services.instrument_service import InstrumentService


def test_cash_asset_never_creates_polling_rule(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR", current_amount="10"))
    assert PollingRuleRepository(db_session).count() == 0


def test_term_deposit_never_creates_polling_rule(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="td", asset_type=AssetType.TERM_DEPOSIT, asset_mode=AssetMode.TERM_DEPOSIT, quote_currency="EUR", principal_amount="100", interest_rate_annual="0.01", start_date="2024-01-01", maturity_date="2024-12-31"))
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


def test_term_deposit_rate_normalization_percent_input(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(
            display_name="td5",
            asset_type=AssetType.TERM_DEPOSIT,
            asset_mode=AssetMode.TERM_DEPOSIT,
            quote_currency="EUR",
            principal_amount="100",
            interest_rate_annual="5",
            start_date="2024-01-01",
            maturity_date="2024-12-31",
        )
    )
    assert asset.interest_rate_annual == Decimal("0.05")


def test_term_deposit_rate_normalization_decimal_input(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(
            display_name="td005",
            asset_type=AssetType.TERM_DEPOSIT,
            asset_mode=AssetMode.TERM_DEPOSIT,
            quote_currency="EUR",
            principal_amount="100",
            interest_rate_annual="0.05",
            start_date="2024-01-01",
            maturity_date="2024-12-31",
        )
    )
    assert asset.interest_rate_annual == Decimal("0.05")
