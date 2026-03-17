from app.models.asset import Asset, AssetMode, AssetType
from app.schemas.asset import AssetCreate


class AssetIdentityService:
    """Builds deterministic identity keys for deduplication across create/import paths."""

    @staticmethod
    def _normalize(value: str | None) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _normalize_upper(value: str | None) -> str:
        return (value or "").strip().upper()

    def key_for_create(self, payload: AssetCreate) -> str:
        mode = payload.asset_mode.value
        quote_currency = self._normalize_upper(payload.quote_currency)
        display_name = self._normalize(payload.display_name)
        exchange = self._normalize(payload.exchange)
        isin = self._normalize_upper(payload.isin)

        if payload.asset_type == AssetType.FUND and isin:
            return f"{mode}|fund|isin:{isin}"
        if payload.asset_mode == AssetMode.CASH:
            return f"cash|quote:{quote_currency}"

        base = f"{mode}|{payload.asset_type.value}|name:{display_name}|ex:{exchange}|quote:{quote_currency}"
        return f"manual|{base}" if payload.is_manual_asset else base

    def key_for_asset(self, asset: Asset) -> str:
        return self.key_for_create(
            AssetCreate(
                display_name=asset.display_name,
                asset_type=asset.asset_type,
                asset_mode=asset.asset_mode,
                quote_currency=asset.quote_currency,
                exchange=asset.exchange,
                isin=asset.isin,
                is_manual_asset=asset.is_manual_asset,
            )
        )

