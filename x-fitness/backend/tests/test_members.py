"""Website sign-up: a pending member with a first payment, seen and confirmed on the admin page, able to verify and pay."""
import pytest
from fastapi.testclient import TestClient

from app import config, llm

NEW = {"first_name": "สมหญิง", "last_name": "ทดสอบ", "phone": "081-234-5678", "package_id": "PKG-12M", "consent": True}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda messages, **kw: "คำตอบทดสอบครับ")
    from app.main import app
    return TestClient(app)


@pytest.fixture
def admin(client):
    token = client.post("/api/admin/login", json={"user": config.ADMIN_USER, "password": config.ADMIN_PASS}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_signup_makes_a_pending_member_with_a_payment_staff_can_see(client, admin):
    r = client.post("/api/members/signup", json={**NEW, "promo_code": "nojoin"})
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["member_id"] == "FN-10021" and s["status"] == "pending"
    assert s["payment"]["amount"] == 990 and "NOJOIN" in s["payment"]["description"]   # joining fee dropped by the code
    assert "phone" not in s
    m = next(x for x in client.get("/api/admin/members", headers=admin).json() if x["member_id"] == s["member_id"])
    assert m["status"] == "pending" and m["phone"] == "081-234-5678" and m["phone_last4"] == "5678"
    pay = next(p for p in client.get("/api/admin/payments", headers=admin).json() if p["id"] == s["payment"]["id"])
    assert pay["status"] == "awaiting_slip" and pay["member_name"] == "สมหญิง ทดสอบ"
    assert client.get("/api/admin/dashboard", headers=admin).json()["signups_pending"] == 1


def test_staff_confirm_or_turn_down_only_new_signups(client, admin):
    mid = client.post("/api/members/signup", json=NEW).json()["member_id"]
    assert client.patch(f"/api/admin/members/{mid}", json={"status": "active"}, headers=admin).json()["status"] == "active"
    assert client.patch(f"/api/admin/members/{mid}", json={"status": "frozen"}, headers=admin).status_code == 422
    assert client.patch("/api/admin/members/FN-99999", json={"status": "active"}, headers=admin).status_code == 404
    assert client.patch(f"/api/admin/members/{mid}", json={"status": "active"}).status_code == 401


def test_frozen_member_cannot_be_changed_from_the_signup_buttons(client, admin):
    frozen = next(m for m in client.get("/api/admin/members", headers=admin).json() if m["status"] == "frozen")
    assert client.patch(f"/api/admin/members/{frozen['member_id']}", json={"status": "active"}, headers=admin).status_code == 409


def test_new_member_verifies_on_the_website_and_in_chat(client):
    s = client.post("/api/members/signup", json=NEW).json()
    v = client.post("/api/members/verify", json={"member_id": s["member_id"], "phone_last4": "5678"})
    assert v.status_code == 200 and v.json()["status"] == "pending" and "phone" not in v.json()
    assert client.post("/api/members/verify", json={"member_id": s["member_id"], "phone_last4": "0000"}).status_code == 404
    reply = client.post("/api/chat", json={"session_id": "K3M8P2Q7R5", "message": "ยอดค้างของฉัน", "member_id": s["member_id"], "phone_last4": "5678"})
    assert reply.status_code == 200


@pytest.mark.parametrize("change, error", [
    ({"phone": "12345"}, "เบอร์โทร"),
    ({"first_name": "<script>"}, "ชื่อ"),
    ({"consent": False}, "ยินยอม"),
    ({"package_id": "PKG-DAY"}, "เคาน์เตอร์"),
    ({"promo_code": "MID2"}, "หมดเขต"),
    ({"promo_code": "YEAR13"}, "ใช้กับแพ็กเกจนี้ไม่ได้"),
])
def test_bad_signups_are_refused(client, change, error):
    r = client.post("/api/members/signup", json={**NEW, **change})
    assert r.status_code == 422 and error in r.json()["detail"]


def test_phone_already_used_is_refused_unless_that_signup_was_turned_down(client, admin):
    first = client.post("/api/members/signup", json=NEW).json()["member_id"]
    again = client.post("/api/members/signup", json={**NEW, "phone": "0812345678"})
    assert again.status_code == 409 and "เบอร์อื่น" in again.json()["detail"]
    assert client.post("/api/members/signup", json={**NEW, "phone": "090-000-0417"}).status_code == 409   # a seed member's phone
    client.patch(f"/api/admin/members/{first}", json={"status": "cancelled"}, headers=admin)
    assert client.post("/api/members/signup", json=NEW).status_code == 201


def test_signups_per_ip_are_limited(client):
    codes = [client.post("/api/members/signup", json={**NEW, "phone": f"08100000{i:02d}"}).status_code for i in range(6)]
    assert codes == [201] * 5 + [429]


def test_annual_with_year13_lasts_13_months():
    from datetime import date
    from app.members import _add_months
    assert _add_months(date(2026, 1, 5), 12) == date(2027, 1, 4)
    assert _add_months(date(2026, 10, 25), 13) == date(2027, 11, 24)
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 27)
