"""
Shared fixtures for the test suite.

Uses an in-memory SQLite database so tests are fully isolated and leave no
files on disk. The `client` fixture provides an async HTTPX client wired to
the FastAPI app with its own fresh database per test.
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Point at an in-memory DB *before* any app code imports the engine
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SIMULATE_SENSORS", "true")

from app.main import app
from app.database import Base, get_db


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """HTTPX async client with the real FastAPI app, database overridden."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Prevent the BLE scanner background task from starting during tests
    from app.services import ble_scanner
    ble_scanner._scanner_instance = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
