from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from src.api import api
from src.modules.health.dependencies import get_health_service
from src.modules.health.schemas import ReadinessResponseSchema
from src.modules.health.service import HealthService

READY_RESULT = ReadinessResponseSchema(
    status="ready",
    checks={"postgres": "up", "redis": "up", "rabbitmq": "up"},
)
NOT_READY_RESULT = ReadinessResponseSchema(
    status="not_ready",
    checks={"postgres": "down", "redis": "up", "rabbitmq": "up"},
)


class StubHealthService:
    def __init__(self, result):
        self.result = result

    async def readiness(self):
        return self.result


@pytest.fixture
def client():
    test_client = TestClient(api.app)
    yield test_client
    api.app.dependency_overrides.clear()


def override_service(result):
    api.app.dependency_overrides[get_health_service] = lambda: StubHealthService(result)


def test_liveness_returns_alive(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["X-Request-ID"]


def test_readiness_returns_200_when_ready(client):
    override_service(READY_RESULT)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"postgres": "up", "redis": "up", "rabbitmq": "up"},
    }


def test_readiness_returns_503_when_not_ready(client):
    override_service(NOT_READY_RESULT)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["postgres"] == "down"


def test_readiness_response_contains_only_statuses(client):
    override_service(NOT_READY_RESULT)

    response = client.get("/health/ready")
    body = response.json()

    assert set(body) == {"status", "checks"}
    assert set(body["checks"]) == {"postgres", "redis", "rabbitmq"}
    assert set(body["checks"].values()) <= {"up", "down"}
    for marker in ("://", "change_me", "password", "secret", "amqp"):
        assert marker not in response.text


def test_health_probe_requests_are_not_logged(client, capsys):
    override_service(READY_RESULT)

    client.get("/health/live")
    client.get("/health/ready")

    out = capsys.readouterr().out
    assert "request_started" not in out
    assert "request_completed" not in out

    client.get("/missing")

    out = capsys.readouterr().out
    assert "request_started" in out


def test_get_health_service_builds_service_from_app_state():
    app = SimpleNamespace(state=SimpleNamespace(message_bus=object()))
    request = Request({"type": "http", "app": app})

    service = get_health_service(request)

    assert isinstance(service, HealthService)
