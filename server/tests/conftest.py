import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db import session as db_session


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    yield
    if db_session._engine is not None:
        await db_session._engine.dispose()
        db_session._engine = None
        db_session._session_maker = None


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
