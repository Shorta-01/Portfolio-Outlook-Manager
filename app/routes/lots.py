from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.schemas.lot import LotCreate
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
