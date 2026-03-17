from app.services.dashboard_service import DashboardService


def test_dashboard_empty(db_session):
    svc = DashboardService(db_session)
    assert svc.owned_rows() == []
    assert svc.watchlist_rows() == []
    assert svc.summary_cards().total_invested == 0

from app.models.asset import AssetMode, AssetType
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.schemas.asset import AssetCreate
from app.services.instrument_service import InstrumentService


def test_default_polling_rule_creation(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="poll", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    assert PollingRuleRepository(db_session).count() == 1


def test_no_polling_rule_for_cash_term_deposit(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR"))
    svc.create_asset(AssetCreate(display_name="td", asset_type=AssetType.TERM_DEPOSIT, asset_mode=AssetMode.TERM_DEPOSIT, quote_currency="EUR"))
    assert PollingRuleRepository(db_session).count() == 0
