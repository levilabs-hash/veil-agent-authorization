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


def test_demo_read_returns_backend_allow():
    response = client.post("/demo/read")
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ALLOW"
    assert body["executed"] is True
    assert body["action"] == "read_email"
