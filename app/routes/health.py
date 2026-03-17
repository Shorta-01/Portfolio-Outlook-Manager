from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.services.status_service import StatusService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/health")
def health(db: Session = Depends(get_db_session)):
    service = StatusService(db)
    return {"status": "ok", "database_reachable": service.database_reachable()}


@router.get("/status", response_class=HTMLResponse)
def status(request: Request, db: Session = Depends(get_db_session)):
    return templates.TemplateResponse(
        "status.html", {"request": request, "status": StatusService(db).build(), "message": request.query_params.get("message")}
    )
