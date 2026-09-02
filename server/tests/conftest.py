from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings


ROBOT_TOKEN = "robot-token-for-tests-123456789"
DASHBOARD_KEY = "dashboard-key-for-tests"


@pytest.fixture
def settings(tmp_path):
    return Settings(
        robot_id="robot-01",
        robot_token=ROBOT_TOKEN,
        dashboard_key=DASHBOARD_KEY,
        event_log_path=tmp_path / "events.jsonl",
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def login():
    def authenticate(client: TestClient) -> None:
        response = client.post(
            "/api/session",
            headers={"X-Session-Mode": "cookie"},
            json={"key": DASHBOARD_KEY},
        )
        assert response.status_code == 200
        assert response.json()["authenticated"] is True
        assert "session" not in response.json()
        assert client.cookies.get("robot_session")
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=strict" in response.headers["set-cookie"].lower()

    return authenticate
