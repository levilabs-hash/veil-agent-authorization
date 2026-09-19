"""Demo console endpoints call VEIL; they do not authorize locally."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_attack_returns_backend_block():
    response = client.post("/demo/attack")
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "BLOCK"
    assert body["executed"] is False
    assert body["provenance"] == "EXTERNAL_EMAIL"
    assert body["action"] == "send_email"


def test_demo_unapproved_send_can_be_approved_through_veil(monkeypatch):
    monkeypatch.setenv("VEIL_OPERATOR_TOKEN", "unit-test-operator-token")
    pending = client.post("/demo/unapproved-send")
    assert pending.status_code == 200
    body = pending.json()
    assert body["decision"] == "REVIEW"
    assert body["executed"] is False
    review_id = body["review_id"]
    assert review_id
    agent_try = client.post(
        "/agent/tools",
        json={
            "tool_name": "send_email",
            "arguments": {"review_id": review_id, "approved": True},
            "claimed_explicit_user_approval": True,
        },
    )
    assert agent_try.status_code == 200
    assert agent_try.json()["executed"] is False
    legacy = client.post(
        "/user/tools",
        json={
            "tool_name": "send_email",
            "resource_id": "reply-draft",
            "recipient": "alex@example.com",
            "explicit_user_approval": True,
        },
    )
    assert legacy.status_code == 200
    assert legacy.json()["executed"] is False
    assert legacy.json()["decision"]["decision"] == "REVIEW"
    resolved = client.post(
        f"/user/reviews/{review_id}/resolve",
        json={"approved": True},
        headers={"Authorization": "Bearer unit-test-operator-token"},
    )
    assert resolved.status_code == 200
    result = resolved.json()
    assert result["executed"] is True
    assert result["decision"]["decision"] == "ALLOW"
    assert result["related_event_id"] == review_id
