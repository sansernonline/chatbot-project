"""Back office: slips staff can see, status switches the bot obeys at once, test-data reset, dashboard from real data."""
import pytest
from fastapi.testclient import TestClient

from app import business, chat, config, llm

SLIP = {"type": "slip", "amount": 990.0, "datetime": "2026-09-25T18:42", "receiver_name": "บจก. เอ็กซ์ ฟิตเนส",
        "receiver_account_last": "4521-0", "reference": "DEMO2609251842A1"}
SID = "K3M8P2Q7R5"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda messages, **kw: "คำตอบทดสอบครับ")
    from app.main import app
    return TestClient(app)


@pytest.fixture
def admin(client):
    token = client.post("/api/admin/login", json={"user": config.ADMIN_USER, "password": config.ADMIN_PASS}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def send_slip(client, monkeypatch, slip=SLIP, member=("FN-10012", "5670"), sid=SID):
    """Customer uploads a slip image, then the chat call carries the vision result (as the website does)."""
    monkeypatch.setattr(chat, "read_image", lambda data, mime: dict(slip))
    vision = client.post("/api/vision", files={"image": ("s.png", b"\x89PNG slip", "image/png")}, data={"session_id": sid}).json()
    return client.post("/api/chat", json={"session_id": sid, "message": "โอนแล้วค่ะ", "member_id": member[0], "phone_last4": member[1],
                                          "vision": vision}).json()


def test_admin_api_needs_login(client):
    for path in ("/api/admin/payments", "/api/admin/bookings", "/api/admin/promotions", "/api/admin/dashboard"):
        assert client.get(path).status_code == 401


def test_slip_goes_on_the_unpaid_payment_and_staff_can_see_it(client, admin, monkeypatch):
    before = {p["id"]: p for p in client.get("/api/admin/payments", headers=admin).json()}
    assert before["PAY-2610-012"]["status"] == "awaiting_slip" and before["PAY-2610-012"]["slips"] == []

    r = send_slip(client, monkeypatch)
    assert r["slip_check"]["ok"] is True and r["slip_check"]["payment_id"] == "PAY-2610-012"

    pay = {p["id"]: p for p in client.get("/api/admin/payments", headers=admin).json()}["PAY-2610-012"]
    assert pay["status"] == "pending_slip" and len(pay["slips"]) == 1 and pay["slips"][0]["ok"] is True
    img = client.get(pay["slips"][0]["url"], headers=admin)
    assert img.status_code == 200 and img.content == b"\x89PNG slip"
    assert client.get(pay["slips"][0]["url"]).status_code == 401                 # the image is for staff only


def test_image_id_from_another_chat_is_ignored(client, admin, monkeypatch):
    monkeypatch.setattr(chat, "read_image", lambda data, mime: dict(SLIP))
    vision = client.post("/api/vision", files={"image": ("s.png", b"\x89PNG", "image/png")}, data={"session_id": "A1B2C3D4E5"}).json()
    client.post("/api/chat", json={"session_id": SID, "message": "สลิป", "member_id": "FN-10012", "phone_last4": "5670", "vision": vision})
    pay = {p["id"]: p for p in client.get("/api/admin/payments", headers=admin).json()}["PAY-2610-012"]
    assert pay["slips"] == [] and pay["status"] == "awaiting_slip"


def test_only_slips_are_kept(client, monkeypatch):
    monkeypatch.setattr(chat, "read_image", lambda data, mime: {"type": "receipt", "total": 1680})
    r = client.post("/api/vision", files={"image": ("r.png", b"\x89PNG", "image/png")}, data={"session_id": SID}).json()
    assert "image_id" not in r and not config.SLIPS_DIR.exists()


def test_same_slip_for_another_payment_fails_reference_check(client, monkeypatch):
    send_slip(client, monkeypatch)
    again = send_slip(client, monkeypatch, member=("FN-10003", "5531"), sid="B2C3D4E5F6")
    assert again["slip_check"]["ok"] is False


def test_staff_confirm_and_bot_sees_it(client, admin):
    assert "ค่าสมาชิกรายเดือน ต.ค. 2569 990.00 บาท" in business.member_context("FN-10012")
    r = client.patch("/api/admin/payments/PAY-2610-012", json={"status": "paid"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "paid"
    assert "ยอดค้างชำระ: ไม่มี" in business.member_context("FN-10012")


def test_promotion_switch_changes_what_the_bot_says(client, admin):
    fact = lambda: " ".join(f for f, _ in business.rules_for("มีโปรอะไรบ้าง"))
    assert "FREECLASS ปิดอยู่" in fact()
    client.patch("/api/admin/promotions/PR-05", json={"status": "active"}, headers=admin)
    assert "FREECLASS (" in fact() and "ใช้ได้" in fact()
    client.patch("/api/admin/promotions/PR-01", json={"status": "inactive"}, headers=admin)
    assert "YEAR13 ปิดอยู่" in fact()


def test_booking_switch_and_bad_input(client, admin):
    assert client.patch("/api/admin/bookings/BK-0013", json={"status": "cancelled"}, headers=admin).json()["status"] == "cancelled"
    assert client.patch("/api/admin/bookings/BK-0013", json={"status": "paid"}, headers=admin).status_code == 422
    assert client.patch("/api/admin/bookings/BK-9999", json={"status": "booked"}, headers=admin).status_code == 404


def test_reset_goes_back_to_seed(client, admin, monkeypatch):
    send_slip(client, monkeypatch)
    client.patch("/api/admin/promotions/PR-05", json={"status": "active"}, headers=admin)
    assert client.post("/api/admin/test-data/reset", headers=admin).status_code == 204
    pays = {p["id"]: p for p in client.get("/api/admin/payments", headers=admin).json()}
    assert pays["PAY-2610-012"]["status"] == "awaiting_slip" and pays["PAY-2610-012"]["slips"] == []
    assert not list(config.SLIPS_DIR.glob("*"))
    assert {p["id"]: p for p in client.get("/api/admin/promotions", headers=admin).json()}["PR-05"]["status"] == "inactive"


def test_seed_slips_show_sample_images(client, admin):
    pays = {p["id"]: p for p in client.get("/api/admin/payments", headers=admin).json()}
    sample = pays["PAY-2609-003"]["slips"][0]
    assert sample["sample"] is True and client.get(sample["url"]).status_code == 200


def test_dashboard_counts_real_data(client, admin):
    client.post(f"/api/conversations/{SID}/messages", json={"from": "user", "text": "สวัสดี"})
    client.post(f"/api/conversations/{SID}/handoff", json={"topic": "ขอคืนเงิน"})
    d = client.get("/api/admin/dashboard", headers=admin).json()
    assert d["chats_today"] == 1 and d["waiting"] == 1 and sum(d["messages_by_hour"]) == 1
    assert d["slips_pending"]["count"] == 3 and d["awaiting_slip"] == 3 and d["handoff_topics"] == [["ขอคืนเงิน", 1]]
    assert d["promotions_active"] == 3 and len(d["messages_by_hour"]) == 24


def test_knowledge_graph_for_admin_only(client, admin):
    assert client.get("/api/admin/kb/graph").status_code == 401
    g = client.get("/api/admin/kb/graph", headers=admin).json()
    ids = {n["id"] for n in g["nodes"]}
    assert len(g["nodes"]) > 100 and g["edges"] and all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    assert any(n["docs"] for n in g["nodes"])                                  # nodes say which KB-xx they came from


def test_api_docs_list_every_endpoint_with_a_summary(client):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    ops = [op for path in spec["paths"].values() for op in path.values()]
    assert all(op.get("summary") for op in ops) and "HTTPBearer" in spec["components"]["securitySchemes"]


def test_database_holds_every_json_table_unchanged():
    """data/db/*.json → SQLite → back: same rows, same fields, same types (business code reads the tables, not the files)."""
    import json
    from app import db
    for name in db.TABLES:
        data = json.loads((config.DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))
        want = data["items"] if "items" in data else {k: v for k, v in data.items() if k != "_note"}
        assert db.business_table(name) == want, name
    assert db.setting("payments", "slip_rule") and db.setting("pt_packages", "trial")


def test_staff_change_stays_until_reset_and_seed_reloads_when_json_changes(client, admin, monkeypatch):
    import json
    from contextlib import closing
    from app import db
    client.patch("/api/admin/promotions/PR-05", json={"status": "active"}, headers=admin)
    with closing(db.connect()) as con:
        assert db.seed_business(con) is False                                   # files unchanged: staff change kept
    assert {p["id"]: p for p in business.table("promotions")}["PR-05"]["status"] == "active"
    real = db._seed_files
    monkeypatch.setattr(db, "_seed_files", lambda: {**real(), "rewards": {"earn": "changed"}})
    with closing(db.connect()) as con:
        assert db.seed_business(con) is True                                    # a data/db file changed: reload
    assert business.table("rewards") == {"earn": "changed"}
    assert {p["id"]: p for p in business.table("promotions")}["PR-05"]["status"] == "inactive"


def test_website_data_comes_from_the_database_without_members(client, admin):
    d = client.get("/api/data").json()
    assert {"business", "packages", "schedule", "pt", "promotions"} <= set(d) and "members" not in d and "payments" not in d
    client.patch("/api/admin/promotions/PR-05", json={"status": "active"}, headers=admin)
    assert {p["id"]: p for p in client.get("/api/data").json()["promotions"]}["PR-05"]["status"] == "active"
    assert client.get("/api/admin/data").status_code == 401
    a = client.get("/api/admin/data", headers=admin).json()
    assert len(a["members"]) == 20 and a["leads"]
