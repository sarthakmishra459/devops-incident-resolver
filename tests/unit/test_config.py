import pytest

from devops_resolver.shared.config import Settings


@pytest.mark.unit
def test_cors_origins_accepts_plain_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIR_CORS_ORIGINS", "https://example.com")

    settings = Settings()

    assert settings.cors_origins == ["https://example.com"]
