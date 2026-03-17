from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.services.dashboard_service import DashboardService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db_session)):
    service = DashboardService(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "rows": service.owned_rows(), "summary": service.summary_cards()},
    )


@router.get("/watchlist", response_class=HTMLResponse)
def watchlist(request: Request, db: Session = Depends(get_db_session)):
    service = DashboardService(db)
    return templates.TemplateResponse("watchlist.html", {"request": request, "rows": service.watchlist_rows()})
