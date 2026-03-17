from app.models.asset import Asset, AssetMode, AssetType
from app.providers.symbol_resolver import SymbolResolver


def make_asset(**kwargs):
    defaults = dict(
        id=1,
        symbol_internal="asset_abcd1234",
        display_name="Sample",
        asset_type=AssetType.STOCK,
        asset_mode=AssetMode.OWNED,
        quote_currency="USD",
        is_manual_asset=False,
        enabled=True,
    )
    defaults.update(kwargs)
    return Asset(**defaults)


def test_no_lookup_for_cash():
    resolved = SymbolResolver().resolve(make_asset(asset_type=AssetType.CASH, asset_mode=AssetMode.CASH))
    assert resolved.lookup_possible is False


def test_no_lookup_for_term_deposit():
    resolved = SymbolResolver().resolve(make_asset(asset_type=AssetType.TERM_DEPOSIT, asset_mode=AssetMode.TERM_DEPOSIT))
    assert resolved.lookup_possible is False


def test_fund_isin_first_resolution():
    resolved = SymbolResolver().resolve(make_asset(asset_type=AssetType.FUND, isin="lu123"))
    assert resolved.lookup_possible is True
    assert resolved.provider_symbol == "LU123"


def test_manual_unresolved_fails_gracefully():
    resolved = SymbolResolver().resolve(make_asset(symbol_internal="", display_name="", is_manual_asset=True))
    assert resolved.lookup_possible is False
    assert "manual" in resolved.lookup_reason.lower()
