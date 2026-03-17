from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.dependencies import get_db_session
from app.main import app


def test_admin_cleanup_run_once_route_redirects():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    def _override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_db
    try:
        client = TestClient(app)
        response = client.post("/admin/cleanup/run-once", follow_redirects=False)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 303
    assert "/status?message=" in response.headers["location"]
