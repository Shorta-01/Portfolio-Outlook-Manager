from app.models.asset import Asset, AssetType
from app.providers.types import ResolvedInstrument


NO_LOOKUP_TYPES = {AssetType.CASH, AssetType.TERM_DEPOSIT}


class SymbolResolver:
    def resolve(self, asset: Asset) -> ResolvedInstrument:
        if asset.asset_type in NO_LOOKUP_TYPES:
            return ResolvedInstrument(None, None, False, f"No lookup for {asset.asset_type.value}", "non_market")

        if asset.provider_primary and asset.provider_symbol_primary:
            return ResolvedInstrument(asset.provider_primary, asset.provider_symbol_primary, True, "Using stored provider symbol", "market")

        if asset.asset_type == AssetType.FUND and asset.isin:
            return ResolvedInstrument("twelve_data", asset.isin.strip().upper(), True, "Fund resolved via ISIN-first", "market")

        if asset.is_manual_asset:
            return ResolvedInstrument(None, None, False, "Manual-only asset cannot be externally resolved", "market")

        fallback_symbol = self._fallback_symbol(asset)
        if fallback_symbol:
            return ResolvedInstrument("twelve_data", fallback_symbol, True, "Using normalized fallback symbol", "market")

        return ResolvedInstrument(None, None, False, "No provider symbol available", "market")

    def _fallback_symbol(self, asset: Asset) -> str | None:
        if asset.isin and asset.asset_type != AssetType.FUND:
            return asset.isin.strip().upper()
        if asset.symbol_internal:
            core = asset.symbol_internal.replace("asset_", "").upper()
            if core:
                return core
        cleaned_name = "".join(ch for ch in asset.display_name.upper() if ch.isalnum() or ch in {".", "-", "_"})
        return cleaned_name or None
