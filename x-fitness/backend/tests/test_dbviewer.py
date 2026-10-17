import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import config, dbviewer
from app.main import app


@pytest.fixture
def admin():
    client = TestClient(app)
    token = client.post("/api/admin/login", json={"user": config.ADMIN_USER, "password": config.ADMIN_PASS}).json()["token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_db_viewer_is_for_admin_only():
    client = TestClient(app)
    assert client.get("/api/admin/db").status_code == 401 and client.get("/api/admin/db/members").status_code == 401


def test_tables_come_with_the_data_dictionary(admin):
    client, h = admin
    d = client.get("/api/admin/db", headers=h).json()
    by = {t["name"]: t for t in d["tables"]}
    assert d["file"] == "xfitness_db.sqlite3" and [t["group"] for t in d["tables"]][0] == "shop"
    assert by["members"]["rows"] == 20 and by["members"]["about"]
    assert all(c["about"] for t in d["tables"] for c in t["columns"]), "every column needs a line in data/db/datadict.json"


def test_rows_page_by_page_and_unknown_table(admin):
    client, h = admin
    page = client.get("/api/admin/db/members?limit=5&offset=5", headers=h).json()
    assert page["total"] == 20 and len(page["rows"]) == 5 and page["columns"][0] == "member_id"
    assert client.get('/api/admin/db/members"; DROP TABLE members; --', headers=h).status_code == 404


def test_connection_cannot_write():
    with pytest.raises(sqlite3.OperationalError):
        dbviewer._read_only().execute("DELETE FROM members")
