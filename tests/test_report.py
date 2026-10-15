import pytest

from ottimizzazione_token.report import compare_input_tokens, format_comparison


def test_confronto_con_risparmio():
    c = compare_input_tokens("claude-opus-5-5", 1_000, 750)
    assert c.tokens_saved == 250
    assert c.saved_pct == pytest.approx(25.0)
    assert c.cost_saved == pytest.approx(250 * 4 / 1e6)


def test_versione_nuova_piu_lunga_risparmio_negativo():
    c = compare_input_tokens("claude-opus-5-5", 100, 150)
    assert c.tokens_saved == -50
    assert c.saved_pct == pytest.approx(-50.0)


def test_prima_vuota_percentuale_zero():
    assert compare_input_tokens("claude-opus-5-5", 0, 0).saved_pct == 0.0


def test_modello_sconosciuto():
    with pytest.raises(ValueError):
        compare_input_tokens("non-esiste", 1, 1)


def test_formato_con_proiezione():
    text = format_comparison(compare_input_tokens("claude-opus-5-5", 1_000_000, 500_000), 1000)
    assert "50.0%" in text
    assert "1,000 richieste: $2,000.00" in text
