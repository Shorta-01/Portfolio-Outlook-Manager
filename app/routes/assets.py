from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.services.asset_detail_service import AssetDetailService
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
    return templates.TemplateResponse("asset_detail.html", {"request": request, **model})
