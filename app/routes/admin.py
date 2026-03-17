from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.repositories.asset_repo import AssetRepository
from app.schemas.quote_fx import FXRateCreate, MarketQuoteCreate
from app.services.market_data_admin_service import MarketDataAdminService
from app.scheduler.jobs import run_polling_cycle

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


@router.get("/quotes/new", response_class=HTMLResponse)
def new_quote_form(request: Request, db: Session = Depends(get_db_session)):
    assets = AssetRepository(db).list_all()
    return templates.TemplateResponse("admin_quote_form.html", {"request": request, "assets": assets, "now": datetime.now(timezone.utc).isoformat()})


@router.post("/quotes")
def create_quote(
    asset_id: int = Form(...),
    provider_name: str = Form(...),
    provider_symbol: str = Form(...),
    price: str = Form(...),
    quote_currency: str = Form(...),
    provider_timestamp_utc: str = Form(...),
    db: Session = Depends(get_db_session),
):
    MarketDataAdminService(db).create_quote(
        MarketQuoteCreate(
            asset_id=asset_id,
            provider_name=provider_name,
            provider_symbol=provider_symbol,
            price=price,
            quote_currency=quote_currency,
            provider_timestamp_utc=provider_timestamp_utc,
        )
    )
    return RedirectResponse(url="/", status_code=303)


@router.get("/fx/new", response_class=HTMLResponse)
def new_fx_form(request: Request):
    return templates.TemplateResponse("admin_fx_form.html", {"request": request, "now": datetime.now(timezone.utc).isoformat()})


@router.post("/fx")
def create_fx(
    base_currency: str = Form(...),
    quote_currency: str = Form(...),
    rate: str = Form(...),
    provider_name: str = Form(...),
    provider_timestamp_utc: str = Form(...),
    db: Session = Depends(get_db_session),
):
    MarketDataAdminService(db).create_fx_rate(
        FXRateCreate(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=rate,
            provider_name=provider_name,
            provider_timestamp_utc=provider_timestamp_utc,
        )
    )
    return RedirectResponse(url="/status", status_code=303)


@router.post("/polling/run-once")
def run_polling_once(db: Session = Depends(get_db_session)):
    run_polling_cycle(db)
    return RedirectResponse(url="/status", status_code=303)
