from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.base import Base
from app.db.session import engine
from app.logging_config import configure_logging
from app.routes import admin, assets, dashboard, health, imports, lots, settings
from app.scheduler.engine import start_scheduler, stop_scheduler
from app.config import settings as app_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)
    if app_settings.scheduler_enabled:
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Portfolio Outlook Manager", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(dashboard.router)
app.include_router(assets.router)
app.include_router(lots.router)
app.include_router(imports.router)
app.include_router(settings.router)
app.include_router(health.router)

app.include_router(admin.router)
