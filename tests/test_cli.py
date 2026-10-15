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


def test_compress_su_file(tmp_path):
    f, out = tmp_path / "p.txt", tmp_path / "out.txt"
    f.write_text("A    b\n\n\n\nC d\n")
    result = runner.invoke(app, ["compress", str(f), "-o", str(out)])
    assert result.exit_code == 0
    assert out.read_text() == "A b\n\nC d"


def test_compress_con_conteggio(mocker, tmp_path):
    _mock_client(mocker, 100, 80)
    f = tmp_path / "p.txt"
    f.write_text("A    b")
    result = runner.invoke(app, ["compress", str(f), "--count"])
    assert result.exit_code == 0
    assert "20 token (20.0%)" in result.output


def test_cache_check_segnala_problemi(mocker, tmp_path):
    _mock_client(mocker, 100)
    f = tmp_path / "system.txt"
    f.write_text("Data: 2026-10-15 10:00")
    result = runner.invoke(app, ["cache-check", str(f), "-m", "claude-opus-5-5"])
    assert result.exit_code == 1
    assert "sotto la soglia" in result.output
    assert "data/ora" in result.output


def test_cache_check_ok(mocker, tmp_path):
    _mock_client(mocker, 5000)
    f = tmp_path / "system.txt"
    f.write_text("Istruzioni stabili")
    result = runner.invoke(app, ["cache-check", str(f), "-m", "claude-opus-5-5"])
    assert result.exit_code == 0


def test_comandi_a_pagamento_richiedono_yes(mocker, tmp_path):
    build = mocker.patch("ottimizzazione_token.cli.build_client")
    f = tmp_path / "p.txt"
    f.write_text('{"custom_id": "a", "prompt": "x"}\n')
    for args in (["batch-submit", str(f)], ["compare", str(f), "-m", "claude-opus-5-5"]):
        result = runner.invoke(app, args)
        assert result.exit_code == 1
        assert "--yes" in result.output
    build.assert_not_called()


def test_batch_submit_custom_id_duplicato(mocker, tmp_path):
    mocker.patch("ottimizzazione_token.cli.build_client")
    f = tmp_path / "p.jsonl"
    f.write_text('{"custom_id": "a", "prompt": "x"}\n{"custom_id": "a", "prompt": "y"}\n')
    result = runner.invoke(app, ["batch-submit", str(f), "--yes"])
    assert result.exit_code == 1
    assert "duplicato" in result.output


def test_batch_submit(mocker, tmp_path):
    client = mocker.Mock()
    client.messages.batches.create.return_value = mocker.Mock(id="batch_9")
    mocker.patch("ottimizzazione_token.cli.build_client", return_value=client)
    f = tmp_path / "p.jsonl"
    f.write_text('{"custom_id": "a", "prompt": "x"}\n\n{"custom_id": "b", "prompt": "y"}\n')
    result = runner.invoke(app, ["batch-submit", str(f), "--yes"])
    assert result.exit_code == 0
    assert "batch_9 (2 richieste)" in result.output


def test_batch_results_in_corso(mocker):
    client = mocker.Mock()
    client.messages.batches.retrieve.return_value = mocker.Mock(processing_status="in_progress")
    mocker.patch("ottimizzazione_token.cli.build_client", return_value=client)
    result = runner.invoke(app, ["batch-results", "batch_1"])
    assert result.exit_code == 0
    assert "in corso" in result.output
    client.messages.batches.results.assert_not_called()
