from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.pragmas import configure_sqlite_pragmas

engine = create_engine(settings.database_url, future=True)
configure_sqlite_pragmas(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
