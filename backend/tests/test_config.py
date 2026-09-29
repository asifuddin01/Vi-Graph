import pytest

from app.config import Settings


def test_defaults_use_mock_vlm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIGRAPH_VLM_BACKEND", raising=False)

    settings = Settings(_env_file=None)

    assert settings.vlm_backend == "mock"
    assert settings.vlm_adapter_path is None


def test_cors_origins_are_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIGRAPH_CORS_ORIGINS", "http://a.test, http://b.test,")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_empty_adapter_path_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIGRAPH_VLM_ADAPTER_PATH", "")

    settings = Settings(_env_file=None)

    assert settings.vlm_adapter_path is None


def test_unknown_vlm_backend_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIGRAPH_VLM_BACKEND", "gpt")

    with pytest.raises(ValueError):
        Settings(_env_file=None)
