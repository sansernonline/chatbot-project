import pytest

from app import config


@pytest.fixture(autouse=True)
def no_real_api(monkeypatch):
    """Tests never call Typhoon even when backend/.env has a key (RAG then uses keyword search)."""
    monkeypatch.setattr(config, "TYPHOON_API_KEY", "")
    monkeypatch.setattr(config, "EMBED_API_KEY", "")
