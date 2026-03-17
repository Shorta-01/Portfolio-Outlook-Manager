import csv
from io import StringIO
from sqlalchemy.orm import Session

from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.schemas.import_models import ImportResult, ImportRowError
from app.schemas.lot import LotCreate
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


class ImportService:
    def __init__(self, db: Session):
        self.db = db
        self.instrument_service = InstrumentService(db)
        self.lot_service = LotService(db)

    def import_csv(self, csv_text: str, import_kind: str) -> ImportResult:
        result = ImportResult()
        reader = csv.DictReader(StringIO(csv_text))
        for i, row in enumerate(reader, start=2):
            try:
                if import_kind == "owned":
                    self._import_owned_row(row)
                elif import_kind == "watchlist":
                    self._import_watchlist_row(row)
                else:
                    raise ValueError("Unsupported import kind")
                result.imported_count += 1
            except Exception as exc:  # noqa: BLE001
                self.db.rollback()
                result.failed_rows.append(ImportRowError(row_number=i, message=str(exc)))
        return result

    def _import_owned_row(self, row: dict[str, str]) -> None:
        asset = self.instrument_service.create_asset(
            AssetCreate(
                display_name=row["display_name"],
                asset_type=AssetType(row["asset_type"]),
                asset_mode=AssetMode.OWNED,
                quote_currency=row["quote_currency"],
                exchange=row.get("exchange"),
                isin=row.get("isin"),
            )
        )
        self.lot_service.create_lot(
            LotCreate(
                asset_id=asset.id,
                quantity=row["quantity"],
                buy_price=row["buy_price"],
                buy_currency=row["buy_currency"],
                buy_date=row["buy_date"],
                fees=row.get("fees") or "0",
                notes=row.get("notes") or None,
            )
        )

    def _import_watchlist_row(self, row: dict[str, str]) -> None:
        self.instrument_service.create_asset(
            AssetCreate(
                display_name=row["display_name"],
                asset_type=AssetType(row["asset_type"]),
                asset_mode=AssetMode.WATCHLIST,
                quote_currency=row["quote_currency"],
                exchange=row.get("exchange"),
                isin=row.get("isin"),
            )
        )
