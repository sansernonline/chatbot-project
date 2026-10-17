import pytest

from app import config, limits


@pytest.fixture(autouse=True)
def no_real_api(monkeypatch):
    """Tests never call Typhoon even when backend/.env has a key (RAG then uses keyword search)."""
    monkeypatch.setattr(config, "TYPHOON_API_KEY", "")
    monkeypatch.setattr(config, "EMBED_API_KEY", "")


@pytest.fixture(autouse=True)
def fresh_limits():
    """Every test starts with no rate-limit or verification counts (they live in memory for the whole process)."""
    limits.reset()


@pytest.fixture(scope="session")
def shop_only_seed(tmp_path_factory):
    """The ready-made database without the sample chats, so tests start with an empty inbox."""
    from app import db
    path = tmp_path_factory.mktemp("seed") / "xfitness_db.sqlite3"
    with pytest.MonkeyPatch.context() as m:
        m.setattr(db, "CHATS", "no-sample-chats.json")
        db.build_seed(path)
    return path


@pytest.fixture(autouse=True)
def own_database(monkeypatch, tmp_path, shop_only_seed):
    """Every test gets its own chat database and slip folder, so admin changes and slips never leak between tests."""
    monkeypatch.setattr(config, "SEED_DB", shop_only_seed)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "xfitness_db.sqlite3")
    monkeypatch.setattr(config, "SLIPS_DIR", tmp_path / "slips")
