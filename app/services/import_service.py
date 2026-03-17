import csv
from io import StringIO

from sqlalchemy.orm import Session

from app.models.asset import AssetMode, AssetType
from app.repositories.lot_repo import LotRepository
from app.schemas.asset import AssetCreate
from app.schemas.import_models import ImportResult, ImportRowError
from app.schemas.lot import LotCreate
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


class ImportService:
    def __init__(self, db: Session):
        self.db = db
        self.instrument_service = InstrumentService(db)
        self.lot_repo = LotRepository(db)
        self.lot_service = LotService(db)

    def import_csv(self, csv_text: str, import_kind: str) -> ImportResult:
        result = ImportResult()
        reader = csv.DictReader(StringIO(csv_text))
        for i, row in enumerate(reader, start=2):
            try:
                if import_kind == "owned":
                    self._import_owned_row(row, result)
                elif import_kind == "watchlist":
                    self._import_watchlist_row(row, result)
                else:
                    raise ValueError("Unsupported import kind")
            except Exception as exc:  # noqa: BLE001
                self.db.rollback()
                result.failed_rows.append(ImportRowError(row_number=i, message=self._friendly_error(exc, row)))
        return result

    def _import_owned_row(self, row: dict[str, str], result: ImportResult) -> None:
        asset, created = self.instrument_service.create_or_reuse_asset(
            AssetCreate(
                display_name=row["display_name"],
                asset_type=AssetType(row["asset_type"]),
                asset_mode=AssetMode.OWNED,
                quote_currency=row["quote_currency"],
                exchange=row.get("exchange"),
                isin=row.get("isin"),
            )
        )
        if created:
            result.assets_created += 1
        else:
            result.assets_reused += 1

        payload = LotCreate(
            asset_id=asset.id,
            quantity=row["quantity"],
            buy_price=row["buy_price"],
            buy_currency=row["buy_currency"],
            buy_date=row["buy_date"],
            fees=row.get("fees") or "0",
            notes=row.get("notes") or None,
        )
        duplicate_lot = self.lot_repo.find_exact_duplicate(
            asset_id=payload.asset_id,
            quantity=payload.quantity,
            buy_price=payload.buy_price,
            buy_date=payload.buy_date,
            buy_currency=payload.buy_currency,
            fees=payload.fees,
            notes=payload.notes,
        )
        if duplicate_lot is not None:
            result.duplicates_skipped += 1
            return

        self.lot_service.create_lot(payload)
        result.lots_created += 1

    def _import_watchlist_row(self, row: dict[str, str], result: ImportResult) -> None:
        _, created = self.instrument_service.create_or_reuse_asset(
            AssetCreate(
                display_name=row["display_name"],
                asset_type=AssetType(row["asset_type"]),
                asset_mode=AssetMode.WATCHLIST,
                quote_currency=row["quote_currency"],
                exchange=row.get("exchange"),
                isin=row.get("isin"),
            )
        )
        if created:
            result.assets_created += 1
        else:
            result.assets_reused += 1
            result.duplicates_skipped += 1

    def _friendly_error(self, exc: Exception, row: dict[str, str]) -> str:
        msg = str(exc)
        if "symbol" in msg.lower() or "resolve" in msg.lower():
            return "Symbol could not be resolved. Please verify name/ISIN/exchange."
        if "quote" in msg.lower():
            return "Quote data missing for this asset."
        if "fx" in msg.lower():
            return "FX conversion missing for this row currency."
        if "asset_type" in msg.lower() or "valid enumeration" in msg.lower() or "valid assettype" in msg.lower():
            return f"Invalid asset type in row ({row.get('asset_type', '')})."
        return msg
