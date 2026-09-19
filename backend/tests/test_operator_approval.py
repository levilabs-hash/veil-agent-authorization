"""HTTP operator gate on review resolve. The engine still authorizes the action."""

from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.core.config import OPERATOR_TOKEN_ENV
from app.main import app

client = TestClient(app)
TEST_TOKEN = "unit-test-operator-token"


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}"}


def test_http_valid_operator_approval_executes(monkeypatch):
    monkeypatch.setenv(OPERATOR_TOKEN_ENV, TEST_TOKEN)
    pending = client.post("/demo/unapproved-send").json()
    assert pending["decision"] == "REVIEW"
    assert pending["executed"] is False
    before = api_routes.gateway.execution_count()
    resolved = client.post(
        f"/user/reviews/{pending['review_id']}/resolve",
        json={"approved": True},
        headers=_auth(),
    )
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["executed"] is True
    assert body["decision"]["decision"] == "ALLOW"
    assert body["related_event_id"] == pending["review_id"]
    assert api_routes.gateway.execution_count() == before + 1
    blob = resolved.text
    assert TEST_TOKEN not in blob
    assert "Bearer" not in blob


def test_http_missing_credential_no_execution(monkeypatch):
    monkeypatch.setenv(OPERATOR_TOKEN_ENV, TEST_TOKEN)
    pending = client.post("/demo/unapproved-send").json()
    before = api_routes.gateway.execution_count()
    resp = client.post(
        f"/user/reviews/{pending['review_id']}/resolve", json={"approved": True}
    )
    assert resp.status_code == 401
    assert api_routes.gateway.execution_count() == before
    assert api_routes.gateway._reviews[pending["review_id"]].status == "pending"


def test_http_invalid_credential_no_execution(monkeypatch):
    monkeypatch.setenv(OPERATOR_TOKEN_ENV, TEST_TOKEN)
    pending = client.post("/demo/unapproved-send").json()
    before = api_routes.gateway.execution_count()
    resp = client.post(
        f"/user/reviews/{pending['review_id']}/resolve",
        json={"approved": True},
        headers={"Authorization": "Bearer wrong-token-value"},
    )
    assert resp.status_code == 401
    assert api_routes.gateway.execution_count() == before
    assert TEST_TOKEN not in resp.text


def test_http_unconfigured_operator_fail_closed(monkeypatch):
    monkeypatch.delenv(OPERATOR_TOKEN_ENV, raising=False)
    pending = client.post("/demo/unapproved-send").json()
    before = api_routes.gateway.execution_count()
    resp = client.post(
        f"/user/reviews/{pending['review_id']}/resolve",
        json={"approved": True},
        headers={"Authorization": "Bearer anything"},
    )
    assert resp.status_code == 503
    assert api_routes.gateway.execution_count() == before
