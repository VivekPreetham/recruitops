import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import get_settings

# --- point the app at the TEST database before anything creates an engine ---
_real = make_url(get_settings().database_url)
os.environ["DATABASE_URL"] = _real.set(database=f"{_real.database}_test").render_as_string(
    hide_password=False
)
get_settings.cache_clear()

import app.db.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    # safety net: never wipe a non-test database
    assert engine.url.database.endswith("_test"), "Refusing to run tests on non-test DB"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE refresh_tokens, jobs, users, organizations RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def client():
    return TestClient(app)