from typer.testing import CliRunner

from ottimizzazione_token.cli import app

runner = CliRunner()


def test_config_non_mostra_la_chiave(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-segreta")
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "impostata" in result.output
    assert "sk-segreta" not in result.output


def test_senza_comando_mostra_aiuto():
    result = runner.invoke(app, [])
    assert "config" in result.output


def test_cost_senza_api(monkeypatch):
    result = runner.invoke(
        app, ["cost", "-m", "claude-opus-5-5", "-i", "1000000", "-o", "1000000", "-n", "10"]
    )
    assert result.exit_code == 0
    assert "Totale           $24.000000" in result.output
    assert "Totale x 10: $240.00" in result.output


def test_cost_modello_sconosciuto():
    result = runner.invoke(app, ["cost", "-m", "boh", "-i", "1"])
    assert result.exit_code == 1


def _mock_client(mocker, *counts):
    client = mocker.Mock()
    client.messages.count_tokens.side_effect = [mocker.Mock(input_tokens=n) for n in counts]
    mocker.patch("ottimizzazione_token.cli.build_client", return_value=client)
    return client


def test_count(mocker, tmp_path):
    _mock_client(mocker, 1234)
    f = tmp_path / "p.txt"
    f.write_text("ciao")
    result = runner.invoke(app, ["count", str(f)])
    assert result.exit_code == 0
    assert "Token di input: 1,234" in result.output


def test_count_file_vuoto(mocker, tmp_path):
    _mock_client(mocker)
    f = tmp_path / "vuoto.txt"
    f.write_text("")
    result = runner.invoke(app, ["count", str(f)])
    assert result.exit_code == 1


def test_diff(mocker, tmp_path):
    _mock_client(mocker, 1000, 600)
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("lungo")
    b.write_text("corto")
    result = runner.invoke(app, ["diff", str(a), str(b)])
    assert result.exit_code == 0
    assert "400 token (40.0%)" in result.output
