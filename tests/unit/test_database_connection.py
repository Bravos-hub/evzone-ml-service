"""
Unit tests for database connection helpers.
"""
import pytest

import src.database.connection as connection


class DummySession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class DummySessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_db_yields_and_closes_session(monkeypatch):
    session = DummySession()

    def fake_session_local():
        return DummySessionContext(session)

    monkeypatch.setattr(connection, "AsyncSessionLocal", fake_session_local)

    gen = connection.get_db()
    db = await gen.__anext__()

    assert db is session

    await gen.aclose()
    assert session.closed is True
