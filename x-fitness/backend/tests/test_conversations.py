import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "chat.sqlite3")
    from app import db
    from app.main import app
    db.init()
    return TestClient(app)


def admin_headers(client):
    token = client.post("/api/admin/login", json={"user": "admin", "password": "1234"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["chat_store"] == "sqlite" and "llm" in h


def test_customer_handoff_then_admin_reply(client):
    assert client.post("/api/conversations/K3M8P2Q7R5/messages", json={"from": "user", "text": "ขอคุยกับพนักงาน"}).status_code == 200
    conv = client.post("/api/conversations/K3M8P2Q7R5/handoff", json={"topic": "ขอคืนเงิน"}).json()
    assert conv["status"] == "waiting" and conv["ticket"] == "K3M8P2Q7R5"

    h = admin_headers(client)
    assert [c["id"] for c in client.get("/api/admin/conversations", headers=h).json()] == ["K3M8P2Q7R5"]
    client.patch("/api/admin/conversations/K3M8P2Q7R5", json={"status": "agent", "agent": "แอดมิน"}, headers=h)
    client.post("/api/admin/conversations/K3M8P2Q7R5/messages", json={"from": "agent", "text": "รับเรื่องแล้วค่ะ", "by": "แอดมิน"}, headers=h)

    mine = client.get("/api/conversations/K3M8P2Q7R5").json()
    assert mine["status"] == "agent"
    assert [m["from"] for m in mine["msgs"]] == ["user", "system", "agent"]


@pytest.mark.parametrize("bad", ["s1", "K3M8P2Q7R", "K3M8P2Q7R55", "33M8P2Q7R5", "k3m8p2q7r5", "KKM8P2Q7R5"])
def test_customer_ticket_format_enforced(client, bad):
    assert client.post(f"/api/conversations/{bad}/messages", json={"from": "user", "text": "a"}).status_code == 422


def test_admin_endpoints_need_login(client):
    assert client.get("/api/admin/conversations").status_code == 401
    assert client.post("/api/admin/login", json={"user": "admin", "password": "wrong"}).status_code == 401


def test_customer_cannot_post_as_agent(client):
    assert client.post("/api/conversations/K3M8P2Q7R5/messages", json={"from": "agent", "text": "hi"}).status_code == 403


def test_seen_patch_does_not_reorder(client):
    h = admin_headers(client)
    before = client.post("/api/conversations/K3M8P2Q7R5/messages", json={"from": "user", "text": "a"}).json()["updated"]
    after = client.patch("/api/admin/conversations/K3M8P2Q7R5", json={"seen_admin": 1, "touch": False}, headers=h).json()
    assert after["updated"] == before and after["seen_admin"] == 1


def test_delete(client):
    h = admin_headers(client)
    client.post("/api/conversations/K3M8P2Q7R5/messages", json={"from": "user", "text": "a"})
    assert client.delete("/api/admin/conversations", headers=h).status_code == 204
    assert client.get("/api/conversations/K3M8P2Q7R5").status_code == 404


def test_serves_mockup(client):
    assert "X Fitness" in client.get("/admin/").text
