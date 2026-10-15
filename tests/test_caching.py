import pytest

from ottimizzazione_token.caching import (
    cache_hit_rate,
    cached_system,
    diagnose_cache,
    find_volatile_content,
    min_cacheable_tokens,
    with_cached_tools,
)
from ottimizzazione_token.pricing import PRICES, UsageTokens


def test_system_con_breakpoint():
    assert cached_system("istruzioni") == [
        {"type": "text", "text": "istruzioni", "cache_control": {"type": "ephemeral"}}
    ]
    assert cached_system("x", "1h")[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_tool_breakpoint_sull_ultimo_senza_modificare_originale():
    tools = [{"name": "a"}, {"name": "b"}]
    result = with_cached_tools(tools)
    assert "cache_control" not in result[0]
    assert result[1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in tools[1]


def test_tool_vuoti():
    with pytest.raises(ValueError):
        with_cached_tools([])


def test_soglie_per_tutti_i_modelli_con_prezzo():
    assert min_cacheable_tokens("claude-opus-5-5") == 512
    assert min_cacheable_tokens("claude-haiku-4-5") == 4096
    for model in PRICES:
        min_cacheable_tokens(model)
    with pytest.raises(ValueError):
        min_cacheable_tokens("boh")


def test_trova_contenuti_variabili():
    text = "Oggi è 2026-10-15 14:03:22, richiesta 123e4567-e89b-12d3-a456-426614174000."
    found = find_volatile_content(text)
    assert any(f.startswith("data/ora") for f in found)
    assert any(f.startswith("UUID") for f in found)
    assert find_volatile_content("Sei un assistente conciso.") == []


def test_hit_rate():
    assert cache_hit_rate(UsageTokens(input_tokens=100, cache_read_tokens=900)) == 0.9
    assert cache_hit_rate(UsageTokens()) == 0.0


def test_diagnosi_cache_sana():
    usages = [
        UsageTokens(input_tokens=50, cache_write_5m_tokens=2000),
        UsageTokens(input_tokens=50, cache_read_tokens=2000),
        UsageTokens(input_tokens=60, cache_read_tokens=2000),
    ]
    assert diagnose_cache(usages) == []


def test_diagnosi_nessuna_cache():
    problems = diagnose_cache([UsageTokens(input_tokens=300)] * 2)
    assert "soglia minima" in problems[0]


def test_diagnosi_prefisso_che_cambia():
    usages = [UsageTokens(cache_write_5m_tokens=2000), UsageTokens(cache_write_5m_tokens=2000)]
    problems = diagnose_cache(usages)
    assert any("[2]" in p for p in problems)
    assert any("riscrive" in p for p in problems)


def test_diagnosi_una_sola_richiesta():
    assert "almeno 2" in diagnose_cache([UsageTokens()])[0]
