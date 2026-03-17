from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.models.alert_rule import AlertRule
from app.repositories.alert_event_repo import AlertEventRepository
from app.repositories.alert_rule_repo import AlertRuleRepository
from app.repositories.asset_repo import AssetRepository
from app.services.alert_engine_service import AlertEngineService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/alerts", response_class=HTMLResponse)
def alerts_page(
    request: Request,
    unread_only: int = Query(default=0),
    severity: str = Query(default=""),
    asset_id: int | None = Query(default=None),
    active_only: int = Query(default=0),
    resolved_only: int = Query(default=0),
    db: Session = Depends(get_db_session),
):
    repo = AlertEventRepository(db)
    rows = repo.list_filtered(
        unread_only=unread_only == 1,
        severity=severity,
        asset_id=asset_id,
        active_only=active_only == 1,
        resolved_only=resolved_only == 1,
    )
    return templates.TemplateResponse(
        "alerts.html",
        {
            "request": request,
            "alerts": rows,
            "assets": AssetRepository(db).list_all(),
            "query": {"unread_only": str(unread_only), "severity": severity, "asset_id": str(asset_id or ""), "active_only": str(active_only), "resolved_only": str(resolved_only)},
        },
    )


@router.post("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db_session)):
    AlertEventRepository(db).mark_read(alert_id)
    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/alerts/mark-all-read")
def mark_all_read(db: Session = Depends(get_db_session)):
    AlertEventRepository(db).mark_all_read()
    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db_session)):
    AlertEventRepository(db).resolve(alert_id)
    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


@router.get("/alerts/rules", response_class=HTMLResponse)
def list_rules(request: Request, db: Session = Depends(get_db_session)):
    return templates.TemplateResponse("alert_rules.html", {"request": request, "rules": AlertRuleRepository(db).list_all(), "assets": AssetRepository(db).list_all()})


@router.get("/alerts/rules/new", response_class=HTMLResponse)
def new_rule(request: Request, db: Session = Depends(get_db_session)):
    return templates.TemplateResponse("alert_rule_form.html", {"request": request, "rule": None, "assets": AssetRepository(db).list_all()})


@router.post("/alerts/rules")
def create_rule(
    rule_type: str = Form(...),
    severity: str = Form("medium"),
    enabled: bool = Form(False),
    asset_id: str = Form(""),
    asset_mode_scope: str = Form(""),
    asset_type_scope: str = Form(""),
    threshold_value: str = Form(""),
    cooldown_minutes: int = Form(60),
    config_json: str = Form(""),
    db: Session = Depends(get_db_session),
):
    rule = AlertRule(
        rule_type=rule_type,
        severity=severity,
        enabled=enabled,
        asset_id=int(asset_id) if asset_id else None,
        asset_mode_scope=asset_mode_scope or None,
        asset_type_scope=asset_type_scope or None,
        threshold_value=threshold_value or None,
        cooldown_minutes=cooldown_minutes,
        config_json=config_json or None,
    )
    AlertRuleRepository(db).add(rule)
    db.commit()
    return RedirectResponse(url="/alerts/rules", status_code=303)


@router.get("/alerts/rules/{rule_id}/edit", response_class=HTMLResponse)
def edit_rule(rule_id: int, request: Request, db: Session = Depends(get_db_session)):
    return templates.TemplateResponse(
        "alert_rule_form.html",
        {"request": request, "rule": AlertRuleRepository(db).get(rule_id), "assets": AssetRepository(db).list_all()},
    )


@router.post("/alerts/rules/{rule_id}")
def update_rule(
    rule_id: int,
    rule_type: str = Form(...),
    severity: str = Form("medium"),
    enabled: bool = Form(False),
    asset_id: str = Form(""),
    asset_mode_scope: str = Form(""),
    asset_type_scope: str = Form(""),
    threshold_value: str = Form(""),
    cooldown_minutes: int = Form(60),
    config_json: str = Form(""),
    db: Session = Depends(get_db_session),
):
    rule = AlertRuleRepository(db).get(rule_id)
    if rule:
        rule.rule_type = rule_type
        rule.severity = severity
        rule.enabled = enabled
        rule.asset_id = int(asset_id) if asset_id else None
        rule.asset_mode_scope = asset_mode_scope or None
        rule.asset_type_scope = asset_type_scope or None
        rule.threshold_value = threshold_value or None
        rule.cooldown_minutes = cooldown_minutes
        rule.config_json = config_json or None
        db.flush()
        db.commit()
    return RedirectResponse(url="/alerts/rules", status_code=303)


@router.get("/alerts/unread-count")
def unread_count(db: Session = Depends(get_db_session)):
    return JSONResponse({"unread": AlertEngineService(db).unread_count()})


@router.post("/admin/alerts/run-once")
def run_alerts_once(db: Session = Depends(get_db_session)):
    try:
        result = AlertEngineService(db).run_once()
        db.commit()
        message = f"Alert run completed. Created {result['created']} alerts and resolved {result['resolved']}."
    except Exception:
        message = "Alert run failed."
    return RedirectResponse(url=f"/status?message={quote_plus(message)}", status_code=303)
