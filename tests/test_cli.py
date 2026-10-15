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
