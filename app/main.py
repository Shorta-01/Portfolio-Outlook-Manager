from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.base import Base
from app.db.session import engine
from app.logging_config import configure_logging
from app.routes import assets, dashboard, health, imports, lots, settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Portfolio Outlook Manager", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(dashboard.router)
app.include_router(assets.router)
app.include_router(lots.router)
app.include_router(imports.router)
app.include_router(settings.router)
app.include_router(health.router)
