from types import SimpleNamespace

import pytest

from ottimizzazione_token.benchmark import compare_variants, run_variant


def _response(output_tokens, stop_reason="end_turn"):
    usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        cache_creation=None,
    )
    return SimpleNamespace(
        usage=usage, stop_reason=stop_reason, content=[SimpleNamespace(type="text", text="ok")]
    )


def test_run_variant_passa_effort(mocker):
    client = mocker.Mock()
    client.messages.create.return_value = _response(100)
    r = run_variant(client, "domanda", "claude-opus-5-5", effort="low")
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["output_config"] == {"effort": "low"}
    assert "system" not in kwargs
    assert r.text == "ok"
    assert r.cost == pytest.approx((1000 * 4 + 100 * 20) / 1e6)


def test_senza_effort_non_invia_output_config(mocker):
    client = mocker.Mock()
    client.messages.create.return_value = _response(10)
    run_variant(client, "d", "claude-haiku-4-5")
    assert "output_config" not in client.messages.create.call_args.kwargs


def test_effort_non_valido_nessuna_chiamata(mocker):
    client = mocker.Mock()
    with pytest.raises(ValueError):
        run_variant(client, "d", "m", effort="altissimo")
    client.messages.create.assert_not_called()


def test_rifiuto_visibile(mocker):
    client = mocker.Mock()
    client.messages.create.return_value = _response(0, stop_reason="refusal")
    assert run_variant(client, "d", "claude-opus-5-5").stop_reason == "refusal"


def test_compare_ordina_per_costo(mocker):
    client = mocker.Mock()
    client.messages.create.side_effect = [_response(500), _response(50)]
    results = compare_variants(client, "d", ["claude-opus-5-5", "claude-sonnet-5-5"], [None])
    assert [r.model for r in results] == ["claude-sonnet-5-5", "claude-opus-5-5"]
