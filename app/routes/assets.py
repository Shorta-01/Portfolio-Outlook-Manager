from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import quote_plus

from app.dependencies import get_db_session
from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.schemas.asset import AssetUpdate
from app.services.asset_detail_service import AssetDetailService
from app.services.history_service import HistoryService
from app.services.instrument_service import InstrumentService

router = APIRouter(prefix="/assets")
templates = Jinja2Templates(directory="app/templates")


@router.get("/new", response_class=HTMLResponse)
def new_asset_form(request: Request):
    return templates.TemplateResponse("asset_form.html", {"request": request, "asset_modes": list(AssetMode), "asset_types": list(AssetType)})


@router.post("")
def create_asset(
    display_name: str = Form(...),
    asset_type: str = Form(...),
    asset_mode: str = Form(...),
    quote_currency: str = Form(...),
    exchange: str | None = Form(None),
    isin: str | None = Form(None),
    current_amount: str | None = Form(None),
    principal_amount: str | None = Form(None),
    interest_rate_annual: str | None = Form(None),
    start_date: str | None = Form(None),
    maturity_date: str | None = Form(None),
    db: Session = Depends(get_db_session),
):
    service = InstrumentService(db)
    asset = service.create_asset(
        AssetCreate(
            display_name=display_name,
            asset_type=AssetType(asset_type),
            asset_mode=AssetMode(asset_mode),
            quote_currency=quote_currency,
            exchange=exchange,
            isin=isin,
            current_amount=current_amount if current_amount else None,
            principal_amount=principal_amount if principal_amount else None,
            interest_rate_annual=interest_rate_annual if interest_rate_annual else None,
            start_date=start_date if start_date else None,
            maturity_date=maturity_date if maturity_date else None,
        )
    )
    return RedirectResponse(url=f"/assets/{asset.id}", status_code=303)


@router.get("/{asset_id}", response_class=HTMLResponse)
def asset_detail(asset_id: int, request: Request, db: Session = Depends(get_db_session)):
    service = AssetDetailService(db)
    try:
        model = service.build(asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        "asset_detail.html",
        {
            "request": request,
            **model,
            "message": request.query_params.get("message"),
            "message_level": request.query_params.get("message_level", "notice"),
            "backfill_outcome": request.query_params.get("backfill_outcome"),
            "backfill_rows": request.query_params.get("backfill_rows"),
        },
    )


@router.get("/{asset_id}/edit", response_class=HTMLResponse)
def edit_asset_form(asset_id: int, request: Request, db: Session = Depends(get_db_session)):
    asset = InstrumentService(db).asset_repo.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return templates.TemplateResponse("asset_edit_form.html", {"request": request, "asset": asset, "message": request.query_params.get("message")})


@router.post("/{asset_id}/edit")
def edit_asset(
    asset_id: int,
    display_name: str = Form(...),
    quote_currency: str = Form(...),
    exchange: str | None = Form(None),
    isin: str | None = Form(None),
    provider_symbol_primary: str | None = Form(None),
    current_amount: str | None = Form(None),
    principal_amount: str | None = Form(None),
    interest_rate_annual: str | None = Form(None),
    start_date: str | None = Form(None),
    maturity_date: str | None = Form(None),
    bank_name: str | None = Form(None),
    db: Session = Depends(get_db_session),
):
    try:
        InstrumentService(db).update_asset(
            asset_id,
            AssetUpdate(
                display_name=display_name,
                quote_currency=quote_currency,
                exchange=exchange,
                isin=isin,
                provider_symbol_primary=provider_symbol_primary,
                current_amount=current_amount if current_amount else None,
                principal_amount=principal_amount if principal_amount else None,
                interest_rate_annual=interest_rate_annual if interest_rate_annual else None,
                start_date=start_date if start_date else None,
                maturity_date=maturity_date if maturity_date else None,
                bank_name=bank_name,
            ),
        )
        message = "Asset updated successfully."
        level = "notice"
    except Exception as exc:  # noqa: BLE001
        message = f"Asset update failed: {exc}"
        level = "warning"
    return RedirectResponse(url=f"/assets/{asset_id}?message={quote_plus(message)}&message_level={level}", status_code=303)


@router.post("/{asset_id}/archive")
def archive_asset(asset_id: int, confirm: str = Form(""), db: Session = Depends(get_db_session)):
    if confirm != "ARCHIVE":
        return RedirectResponse(url=f"/assets/{asset_id}?message={quote_plus('Archive cancelled. Type ARCHIVE to confirm.')}&message_level=warning", status_code=303)
    InstrumentService(db).archive_asset(asset_id)
    return RedirectResponse(url=f"/?message={quote_plus('Asset archived and excluded from active portfolio views.')}&message_level=notice", status_code=303)


@router.post("/{asset_id}/delete")
def delete_asset(asset_id: int, confirm: str = Form(""), db: Session = Depends(get_db_session)):
    if confirm != "DELETE":
        return RedirectResponse(url=f"/assets/{asset_id}?message={quote_plus('Delete cancelled. Type DELETE to confirm.')}&message_level=warning", status_code=303)
    try:
        InstrumentService(db).delete_asset_if_safe(asset_id)
    except ValueError as exc:
        return RedirectResponse(url=f"/assets/{asset_id}?message={quote_plus(str(exc))}&message_level=warning", status_code=303)
    return RedirectResponse(url=f"/watchlist?message={quote_plus('Watchlist asset deleted.')}&message_level=notice", status_code=303)


@router.post("/{asset_id}/backfill")
def backfill_asset(asset_id: int, db: Session = Depends(get_db_session)):
    result = HistoryService(db).backfill_asset_by_id(asset_id)
    message = result.get("user_message", "Backfill finished.")
    message_level = "notice" if result.get("success") else "warning"
    return RedirectResponse(
        url=(
            f"/assets/{asset_id}?message={quote_plus(message)}"
            f"&message_level={message_level}"
            f"&backfill_outcome={quote_plus(result.get('outcome', 'unknown'))}"
            f"&backfill_rows={result.get('rows_inserted_quotes', 0)}"
        ),
        status_code=303,
    )


@router.post("/{asset_id}/promote")
def promote_watchlist_asset(asset_id: int, db: Session = Depends(get_db_session)):
    InstrumentService(db).promote_watchlist_to_owned(asset_id)
    return RedirectResponse(url=f"/assets/{asset_id}?message=Asset promoted to owned. Add at least one lot to include it in position math.", status_code=303)
