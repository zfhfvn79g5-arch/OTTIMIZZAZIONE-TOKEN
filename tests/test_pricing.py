from types import SimpleNamespace

import pytest

from ottimizzazione_token.pricing import PRICES, UsageTokens, compute_cost


def test_costo_completo_opus():
    usage = UsageTokens(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_write_5m_tokens=1_000_000,
        cache_write_1h_tokens=1_000_000,
        cache_read_tokens=1_000_000,
    )
    c = compute_cost("claude-opus-5-5", usage)
    assert c.input == pytest.approx(4)
    assert c.output == pytest.approx(20)
    assert c.cache_write == pytest.approx(5 + 8)
    assert c.cache_read == pytest.approx(0.20)
    assert c.total == pytest.approx(37.20)


def test_batch_e_inferenza_us_si_combinano():
    usage = UsageTokens(input_tokens=1_000_000)
    c = compute_cost("claude-sonnet-5-5", usage, batch=True, us_inference=True)
    assert c.total == pytest.approx(2 * 0.5 * 1.1)


def test_haiku_5_5_fascia_contesto_lungo():
    sotto = compute_cost("claude-haiku-5-5", UsageTokens(input_tokens=100_000))
    assert not sotto.long_context
    assert sotto.input == pytest.approx(0.01)
    # Motivo: la soglia conta anche le letture dalla cache.
    sopra = compute_cost(
        "claude-haiku-5-5", UsageTokens(input_tokens=60_000, cache_read_tokens=60_000)
    )
    assert sopra.long_context
    assert sopra.input == pytest.approx(60_000 * 0.50 / 1e6)
    assert sopra.cache_read == pytest.approx(60_000 * 0.05 / 1e6)


def test_zero_token_costo_zero():
    assert compute_cost("claude-opus-5-5", UsageTokens()).total == 0


def test_modello_sconosciuto():
    with pytest.raises(ValueError, match="Modello sconosciuto"):
        compute_cost("gpt-5", UsageTokens(input_tokens=1))


def test_inference_geo_non_supportato():
    with pytest.raises(ValueError, match="inference_geo"):
        compute_cost("claude-haiku-4-5", UsageTokens(input_tokens=1), us_inference=True)


def test_token_negativi_rifiutati():
    with pytest.raises(ValueError):
        UsageTokens(input_tokens=-1)


def test_from_usage_con_dettaglio_ttl():
    usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=20,
        cache_creation_input_tokens=300,
        cache_read_input_tokens=40,
        cache_creation=SimpleNamespace(
            ephemeral_5m_input_tokens=100, ephemeral_1h_input_tokens=200
        ),
    )
    t = UsageTokens.from_usage(usage)
    assert (t.cache_write_5m_tokens, t.cache_write_1h_tokens) == (100, 200)
    assert t.prompt_tokens == 10 + 300 + 40


def test_from_usage_dict_senza_dettaglio_e_campi_none():
    t = UsageTokens.from_usage(
        {
            "input_tokens": 5,
            "output_tokens": 1,
            "cache_creation_input_tokens": 7,
            "cache_read_input_tokens": None,
        }
    )
    assert t.cache_write_5m_tokens == 7
    assert t.cache_write_1h_tokens == 0
    assert t.cache_read_tokens == 0


def test_listino_coerente():
    for model, pricing in PRICES.items():
        p = pricing.standard
        assert p.cache_write_5m == pytest.approx(p.input * 1.25), model
        assert p.cache_write_1h == pytest.approx(p.input * 2), model
        assert p.cache_read < p.input, model
