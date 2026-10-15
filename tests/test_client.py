from ottimizzazione_token.client import build_client
from ottimizzazione_token.config import Settings


def test_passa_chiave_e_opzioni(mocker):
    costruttore = mocker.patch("ottimizzazione_token.client.anthropic.Anthropic")
    build_client(Settings(ANTHROPIC_API_KEY="sk-test", max_retries=5, timeout=10))
    costruttore.assert_called_once_with(api_key="sk-test", max_retries=5, timeout=10.0)


def test_senza_chiave_lascia_risolvere_sdk(mocker):
    costruttore = mocker.patch("ottimizzazione_token.client.anthropic.Anthropic")
    build_client(Settings())
    assert "api_key" not in costruttore.call_args.kwargs


def test_legge_impostazioni_se_non_fornite(mocker, monkeypatch):
    monkeypatch.setenv("OTTIMIZZAZIONE_MAX_RETRIES", "0")
    costruttore = mocker.patch("ottimizzazione_token.client.anthropic.Anthropic")
    build_client()
    assert costruttore.call_args.kwargs["max_retries"] == 0
