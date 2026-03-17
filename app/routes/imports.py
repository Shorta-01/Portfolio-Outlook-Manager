from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db_session
from app.services.import_service import ImportService

router = APIRouter(prefix="/imports")
templates = Jinja2Templates(directory="app/templates")


@router.get("/csv", response_class=HTMLResponse)
def csv_form(request: Request):
    return templates.TemplateResponse("import_csv.html", {"request": request})


@router.post("/csv", response_class=HTMLResponse)
async def csv_import(request: Request, import_kind: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db_session)):
    content = (await file.read()).decode("utf-8")
    result = ImportService(db).import_csv(content, import_kind)
    return templates.TemplateResponse("import_csv.html", {"request": request, "result": result, "import_kind": import_kind})
