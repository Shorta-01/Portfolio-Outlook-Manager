from app.services.dashboard_service import DashboardService


def test_dashboard_empty(db_session):
    svc = DashboardService(db_session)
    assert svc.owned_rows() == []
    assert svc.watchlist_rows() == []
    summary = svc.summary_cards()
    assert summary.total_invested == 0
    assert summary.total_current_value == 0
