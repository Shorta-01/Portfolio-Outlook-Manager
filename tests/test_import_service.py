from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.services.import_service import ImportService


def test_csv_import_owned(db_session):
    csv_text = "display_name,asset_type,quote_currency,exchange,isin,quantity,buy_price,buy_currency,buy_date,fees,notes\nA,stock,EUR,,ISIN1,1,10,EUR,2024-01-01,0,n\n"
    result = ImportService(db_session).import_csv(csv_text, "owned")
    assert result.imported_count == 1


def test_csv_import_watchlist(db_session):
    csv_text = "display_name,asset_type,quote_currency,exchange,isin,notes\nW,stock,EUR,,ISIN2,n\n"
    result = ImportService(db_session).import_csv(csv_text, "watchlist")
    assert result.imported_count == 1
    assets = AssetRepository(db_session).list_by_mode(AssetMode.WATCHLIST)
    assert len(assets) == 1
