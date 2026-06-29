import os

import pytest

from devops_resolver.presentation.api.dependencies import get_container
from devops_resolver.shared.config import get_settings


@pytest.fixture(autouse=True)
def clear_singletons(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DIR_ENVIRONMENT", "test")
    monkeypatch.setenv("DIR_USE_MOCK_LLM", "true")
    get_settings.cache_clear()
    get_container.cache_clear()
    yield
    get_container.cache_clear()
    get_settings.cache_clear()
    os.environ.pop("DIR_ENVIRONMENT", None)
