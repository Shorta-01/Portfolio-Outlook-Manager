from urllib.parse import quote_plus

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports")


@router.get('/portfolio.csv', response_class=PlainTextResponse)
def export_portfolio_csv(db: Session = Depends(get_db_session)):
    return PlainTextResponse(ExportService(db).portfolio_csv(), media_type='text/csv')


@router.get('/portfolio-lots.csv', response_class=PlainTextResponse)
def export_portfolio_lots_csv(db: Session = Depends(get_db_session)):
    return PlainTextResponse(ExportService(db).lots_csv(), media_type='text/csv')


@router.get('/watchlist.csv', response_class=PlainTextResponse)
def export_watchlist_csv(db: Session = Depends(get_db_session)):
    return PlainTextResponse(ExportService(db).watchlist_csv(), media_type='text/csv')


@router.post('/backup-db')
def backup_database(db: Session = Depends(get_db_session)):
    target = ExportService(db).create_sqlite_backup()
    return RedirectResponse(url=f"/status?message={quote_plus(f'Backup created: {target}')}", status_code=303)
