from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import quote_plus
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.repositories.asset_repo import AssetRepository
from app.schemas.quote_fx import FXRateCreate, MarketQuoteCreate
from app.services.market_data_admin_service import MarketDataAdminService
from app.scheduler.jobs import run_polling_cycle
from app.services.outlook_service import OutlookService
from app.services.outlook_evaluation_service import OutlookEvaluationService
from app.services.scheduler_state import scheduler_state

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
    try:
        run_polling_cycle(db)
        message = "Polling run completed."
    except Exception:
        message = "Polling run failed. Check provider configuration and symbol mapping."
    return RedirectResponse(url=f"/status?message={quote_plus(message)}", status_code=303)


@router.post("/outlook/run-once")
def run_outlook_once(db: Session = Depends(get_db_session)):
    try:
        OutlookService(db).run_once_for_eligible_assets()
        message = "Outlook run completed."
    except Exception:
        message = "Outlook run failed. Ensure assets have enough history."
    return RedirectResponse(url=f"/status?message={quote_plus(message)}", status_code=303)


@router.post("/outlook/evaluate-run-once")
def run_outlook_evaluate_once(db: Session = Depends(get_db_session)):
    try:
        result = OutlookEvaluationService(db).run_once()
        scheduler_state.last_successful_outlook_evaluation_run_utc = datetime.utcnow()
        scheduler_state.evaluated_outlook_count = result["evaluated_outlook_count"]
        scheduler_state.unevaluated_outlook_count = result["unevaluated_outlook_count"]
        message = "Outlook evaluation completed."
    except Exception:
        message = "Outlook evaluation failed. Verify quote history coverage."
    return RedirectResponse(url=f"/status?message={quote_plus(message)}", status_code=303)
