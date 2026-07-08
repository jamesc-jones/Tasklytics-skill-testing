import json
import os

# Must be set before any `app.*` module is imported: app.database, app.auth.auth_utils,
# and app.services.ai.claude_client all read these at import time and either raise
# (DATABASE_URL, SECRET_KEY) or fail to construct the Anthropic client (ANTHROPIC_API_KEY)
# if they're missing. setdefault() so a real local .env is never clobbered if one is loaded.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key-unused-network-is-mocked")
os.environ.setdefault("ENV", "test")

import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User
from app.auth.auth_utils import hash_password, create_access_token


@pytest.fixture()
def db_session():
    """A fresh, isolated in-memory SQLite DB per test.

    StaticPool + check_same_thread=False keep the single in-memory connection
    alive across the threads FastAPI's TestClient uses for async endpoints
    (like /chat) -- without it, the app and the test would each see a
    different, empty in-memory database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """TestClient with the real get_db dependency swapped for the isolated test session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db_session):
    user = User(
        email="chat-tester@example.com",
        hashed_password=hash_password("TestPassword123!"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(test_user):
    """Real JWT for the seeded test_user, exercising the full get_current_user chain
    (decode + DB lookup) instead of bypassing auth with a dependency override."""
    token = create_access_token(
        {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def mock_call_claude(monkeypatch):
    """Stubs the Claude API call so no network request is ever made.

    Patched at app.ai_agents.chat_agent.call_claude -- that module does
    `from app.services.ai.claude_client import call_claude`, which binds its
    own local name at import time. Patching the original definition in
    claude_client.py would not affect the reference chat_agent.py already holds.
    """
    mock = MagicMock(
        return_value=json.dumps(
            {
                "response": "Here's what to focus on.",
                "priority_tasks": ["Finish quarterly report"],
                "insight": "You complete high-priority tasks fastest earlier in the day.",
            }
        )
    )
    monkeypatch.setattr("app.ai_agents.chat_agent.call_claude", mock)
    return mock
