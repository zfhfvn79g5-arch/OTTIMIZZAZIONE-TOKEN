import pytest


@pytest.fixture(autouse=True)
def ambiente_pulito(monkeypatch, tmp_path):
    """Isola i test da variabili d'ambiente e da un eventuale .env reale."""
    for name in (
        "ANTHROPIC_API_KEY",
        "OTTIMIZZAZIONE_DEFAULT_MODEL",
        "OTTIMIZZAZIONE_MAX_RETRIES",
        "OTTIMIZZAZIONE_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
