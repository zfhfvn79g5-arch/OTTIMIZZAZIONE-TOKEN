import pytest
from pydantic import ValidationError

from ottimizzazione_token.config import DEFAULT_MODEL, Settings


def test_valori_di_default():
    settings = Settings()
    assert settings.default_model == DEFAULT_MODEL
    assert settings.anthropic_api_key is None
    assert settings.max_retries == 2


def test_legge_variabili_e_file_env(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-test\nOTTIMIZZAZIONE_TIMEOUT=30\n")
    monkeypatch.setenv("OTTIMIZZAZIONE_DEFAULT_MODEL", "claude-sonnet-5-5")
    settings = Settings()
    assert settings.anthropic_api_key.get_secret_value() == "sk-test"
    assert settings.timeout == 30
    assert settings.default_model == "claude-sonnet-5-5"


def test_chiave_non_esposta_in_repr(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-segreta")
    assert "sk-segreta" not in repr(Settings())


def test_valori_non_validi(monkeypatch):
    monkeypatch.setenv("OTTIMIZZAZIONE_MAX_RETRIES", "-1")
    with pytest.raises(ValidationError):
        Settings()
