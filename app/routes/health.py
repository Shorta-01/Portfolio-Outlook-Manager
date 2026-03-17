from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.config import settings as app_settings
from app.services.maintenance_service import MaintenanceService
from app.services.status_service import StatusService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/health")
def health(db: Session = Depends(get_db_session)):
    service = StatusService(db)
    return {"status": "ok", "database_reachable": service.database_reachable()}


@router.get("/status", response_class=HTMLResponse)
def status(request: Request, db: Session = Depends(get_db_session)):
    status_payload = StatusService(db).build()
    status_payload["app_version"] = app_settings.app_version
    status_payload["app_build"] = app_settings.app_build
    status_payload["app_environment"] = app_settings.app_environment
    return templates.TemplateResponse(
        "status.html", {"request": request, "status": status_payload, "message": request.query_params.get("message")}
    )


@router.get("/maintenance", response_class=HTMLResponse)
def maintenance(request: Request, db: Session = Depends(get_db_session)):
    report = MaintenanceService(db).scan()
    return templates.TemplateResponse("maintenance.html", {"request": request, **report})
