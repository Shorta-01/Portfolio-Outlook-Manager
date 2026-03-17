from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db_session)):
    repo = SettingsRepository(db)
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "settings": repo.get_first(), "polling_rules": PollingRuleRepository(db).list_all()},
    )


@router.post("/settings")
def update_settings(
    portfolio_base_currency: str = Form(...),
    default_poll_every_minutes: int = Form(...),
    use_market_hours_default: bool = Form(False),
    db: Session = Depends(get_db_session),
):
    repo = SettingsRepository(db)
    repo.upsert(
        {
            "portfolio_base_currency": portfolio_base_currency,
            "default_poll_every_minutes": default_poll_every_minutes,
            "use_market_hours_default": use_market_hours_default,
        }
    )
    db.commit()
    return RedirectResponse(url="/settings", status_code=303)
