from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import quote_plus

from app.dependencies import get_db_session
from app.schemas.lot import LotCreate
from app.schemas.lot import LotUpdate
from app.services.lot_service import LotService

router = APIRouter(prefix="/lots")
templates = Jinja2Templates(directory="app/templates")


@router.get("/new", response_class=HTMLResponse)
def new_lot_form(request: Request, asset_id: int | None = None):
    return templates.TemplateResponse("lot_form.html", {"request": request, "asset_id": asset_id})


@router.post("")
def create_lot(
    asset_id: int = Form(...),
    quantity: str = Form(...),
    buy_price: str = Form(...),
    buy_currency: str = Form(...),
    buy_date: str = Form(...),
    fees: str = Form("0"),
    notes: str | None = Form(None),
    db: Session = Depends(get_db_session),
):
    service = LotService(db)
    try:
        lot = service.create_lot(
            LotCreate(
                asset_id=asset_id,
                quantity=quantity,
                buy_price=buy_price,
                buy_currency=buy_currency,
                buy_date=buy_date,
                fees=fees,
                notes=notes,
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/assets/{lot.asset_id}", status_code=303)


@router.get("/{lot_id}/edit", response_class=HTMLResponse)
def edit_lot_form(lot_id: int, request: Request, db: Session = Depends(get_db_session)):
    lot = LotService(db).lot_repo.get(lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot not found")
    return templates.TemplateResponse("lot_edit_form.html", {"request": request, "lot": lot})


@router.post("/{lot_id}/edit")
def edit_lot(
    lot_id: int,
    quantity: str = Form(...),
    buy_price: str = Form(...),
    buy_currency: str = Form(...),
    buy_date: str = Form(...),
    fees: str = Form("0"),
    notes: str | None = Form(None),
    db: Session = Depends(get_db_session),
):
    try:
        lot = LotService(db).update_lot(lot_id, LotUpdate(quantity=quantity, buy_price=buy_price, buy_currency=buy_currency, buy_date=buy_date, fees=fees, notes=notes))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/assets/{lot.asset_id}?message={quote_plus('Lot updated successfully.')}&message_level=notice", status_code=303)


@router.post("/{lot_id}/delete")
def delete_lot(lot_id: int, confirm: str = Form(""), db: Session = Depends(get_db_session)):
    if confirm != "DELETE":
        lot = LotService(db).lot_repo.get(lot_id)
        aid = lot.asset_id if lot else 0
        return RedirectResponse(url=f"/assets/{aid}?message={quote_plus('Lot delete cancelled. Type DELETE to confirm.')}&message_level=warning", status_code=303)
    asset_id = LotService(db).delete_lot(lot_id)
    return RedirectResponse(url=f"/assets/{asset_id}?message={quote_plus('Lot deleted. Portfolio totals/history may change.')}&message_level=warning", status_code=303)
