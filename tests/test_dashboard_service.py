from app.services.dashboard_service import DashboardService


def test_dashboard_empty(db_session):
    svc = DashboardService(db_session)
    assert svc.owned_rows() == []
    assert svc.watchlist_rows() == []
    assert svc.summary_cards().total_invested == 0
