from types import SimpleNamespace

import pytest

from ottimizzazione_token.counting import count_file, count_text, count_tokens


@pytest.fixture
def client(mocker):
    c = mocker.Mock()
    c.messages.count_tokens.return_value = SimpleNamespace(input_tokens=42)
    return c


def test_count_tokens_passa_solo_parametri_presenti(client):
    msgs = [{"role": "user", "content": "ciao"}]
    assert count_tokens(client, "claude-opus-5-5", msgs) == 42
    client.messages.count_tokens.assert_called_once_with(model="claude-opus-5-5", messages=msgs)


def test_count_tokens_con_system_e_tools(client):
    tools = [{"name": "t", "description": "d", "input_schema": {"type": "object"}}]
    count_tokens(client, "m", [], system="sys", tools=tools)
    kwargs = client.messages.count_tokens.call_args.kwargs
    assert kwargs["system"] == "sys"
    assert kwargs["tools"] == tools


def test_count_file(client, tmp_path):
    f = tmp_path / "prompt.txt"
    f.write_text("è un prompt", encoding="utf-8")
    assert count_file(client, f, "m") == 42
    msgs = client.messages.count_tokens.call_args.kwargs["messages"]
    assert msgs == [{"role": "user", "content": "è un prompt"}]


def test_testo_vuoto_rifiutato_senza_chiamare_api(client):
    with pytest.raises(ValueError, match="vuoto"):
        count_text(client, "   \n", "m")
    client.messages.count_tokens.assert_not_called()


def test_file_inesistente(client, tmp_path):
    with pytest.raises(FileNotFoundError):
        count_file(client, tmp_path / "manca.txt", "m")
