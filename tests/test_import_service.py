from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.services.import_service import ImportService


def test_csv_import_owned_reuses_asset_and_creates_lots(db_session):
    csv_text = (
        "display_name,asset_type,quote_currency,exchange,isin,quantity,buy_price,buy_currency,buy_date,fees,notes\n"
        "A,stock,EUR,,ISIN1,1,10,EUR,2024-01-01,0,n1\n"
        "A,stock,EUR,,ISIN1,2,11,EUR,2024-01-02,1,n2\n"
    )
    result = ImportService(db_session).import_csv(csv_text, "owned")
    assert result.assets_created == 1
    assert result.assets_reused == 1
    assert result.lots_created == 2
    assert result.duplicates_skipped == 0


def test_csv_import_watchlist_duplicate_skipped(db_session):
    csv_text = "display_name,asset_type,quote_currency,exchange,isin,notes\nW,stock,EUR,,ISIN2,n\nW,stock,EUR,,ISIN2,n\n"
    result = ImportService(db_session).import_csv(csv_text, "watchlist")
    assert result.assets_created == 1
    assert result.assets_reused == 1
    assert result.duplicates_skipped == 1
    assets = AssetRepository(db_session).list_by_mode(AssetMode.WATCHLIST)
    assert len(assets) == 1


def test_csv_import_owned_exact_duplicate_lot_skipped(db_session):
    csv_text = (
        "display_name,asset_type,quote_currency,exchange,isin,quantity,buy_price,buy_currency,buy_date,fees,notes\n"
        "A,stock,EUR,,ISIN1,1,10,EUR,2024-01-01,0,n\n"
        "A,stock,EUR,,ISIN1,1,10,EUR,2024-01-01,0,n\n"
    )
    result = ImportService(db_session).import_csv(csv_text, "owned")
    assert result.assets_created == 1
    assert result.assets_reused == 1
    assert result.lots_created == 1
    assert result.duplicates_skipped == 1
    asset = AssetRepository(db_session).list_by_mode(AssetMode.OWNED)[0]
    assert len(LotRepository(db_session).list_for_asset(asset.id)) == 1
