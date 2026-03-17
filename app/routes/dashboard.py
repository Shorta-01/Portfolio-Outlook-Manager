from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.services.dashboard_service import DashboardService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _ui_context(rows, query: dict):
    return {
        "query": query,
        "filter_options": {
            "asset_types": sorted({r.asset_type if hasattr(r, "asset_type") else r["asset_type"] for r in rows}),
            "currencies": sorted({(r.quote_currency if hasattr(r, "quote_currency") else r.get("quote_currency")) for r in rows if (r.quote_currency if hasattr(r, "quote_currency") else r.get("quote_currency"))}),
            "outlooks": sorted({(r.outlook if hasattr(r, "outlook") else r.get("outlook")) for r in rows if (r.outlook if hasattr(r, "outlook") else r.get("outlook"))}),
            "actions": sorted({(r.suggested_action if hasattr(r, "suggested_action") else r.get("suggested_action")) for r in rows if (r.suggested_action if hasattr(r, "suggested_action") else r.get("suggested_action"))}),
            "freshness": sorted({(r.freshness_status if hasattr(r, "freshness_status") else r.get("freshness_status")) for r in rows if (r.freshness_status if hasattr(r, "freshness_status") else r.get("freshness_status"))}),
            "sources": sorted({(r.source_label if hasattr(r, "source_label") else r.get("source_label")) for r in rows if (r.source_label if hasattr(r, "source_label") else r.get("source_label"))}),
        },
    }


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    q: str = Query(default=""),
    sort: str = Query(default="asset_name"),
    dir: str = Query(default="asc"),
    asset_type: str = Query(default=""),
    currency: str = Query(default=""),
    outlook: str = Query(default=""),
    action: str = Query(default=""),
    freshness: str = Query(default=""),
    source: str = Query(default=""),
    incomplete_only: int = Query(default=0),
    db: Session = Depends(get_db_session),
):
    service = DashboardService(db)
    query = {
        "q": q,
        "sort": sort,
        "dir": dir,
        "asset_type": asset_type,
        "currency": currency,
        "outlook": outlook,
        "action": action,
        "freshness": freshness,
        "source": source,
        "incomplete_only": str(incomplete_only),
    }
    rows = service.query_owned_rows(query)
    all_rows = service.owned_rows()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "rows": rows,
            "summary": service.summary_cards(),
            "message": request.query_params.get("message"),
            "message_level": request.query_params.get("message_level", "notice"),
            **_ui_context(all_rows, query),
        },
    )


@router.get("/watchlist", response_class=HTMLResponse)
def watchlist(
    request: Request,
    q: str = Query(default=""),
    sort: str = Query(default="display_name"),
    dir: str = Query(default="asc"),
    asset_type: str = Query(default=""),
    currency: str = Query(default=""),
    outlook: str = Query(default=""),
    action: str = Query(default=""),
    freshness: str = Query(default=""),
    source: str = Query(default=""),
    db: Session = Depends(get_db_session),
):
    service = DashboardService(db)
    query = {
        "q": q,
        "sort": sort,
        "dir": dir,
        "asset_type": asset_type,
        "currency": currency,
        "outlook": outlook,
        "action": action,
        "freshness": freshness,
        "source": source,
    }
    rows = service.query_watchlist_rows(query)
    all_rows = service.watchlist_rows()
    return templates.TemplateResponse(
        "watchlist.html",
        {
            "request": request,
            "rows": rows,
            "message": request.query_params.get("message"),
            "message_level": request.query_params.get("message_level", "notice"),
            **_ui_context(all_rows, query),
        },
    )
