from types import SimpleNamespace

import pytest

from ottimizzazione_token.batching import (
    batch_cost,
    build_requests,
    collect_results,
    submit_batch,
    wait_for_batch,
)


def test_build_requests():
    reqs = build_requests({"a": "uno", "b": "due"}, "claude-haiku-5-5", max_tokens=100, system="s")
    assert [r["custom_id"] for r in reqs] == ["a", "b"]
    assert reqs[0]["params"]["messages"] == [{"role": "user", "content": "uno"}]
    assert reqs[0]["params"]["system"] == "s"
    assert reqs[0]["params"]["max_tokens"] == 100


def test_build_requests_vuoto():
    with pytest.raises(ValueError):
        build_requests({}, "m")


def test_submit(mocker):
    client = mocker.Mock()
    client.messages.batches.create.return_value = SimpleNamespace(id="batch_1")
    assert submit_batch(client, []) == "batch_1"


def test_wait_fa_polling_fino_a_ended(mocker):
    client = mocker.Mock()
    client.messages.batches.retrieve.side_effect = [
        SimpleNamespace(processing_status="in_progress"),
        SimpleNamespace(processing_status="ended"),
    ]
    sleeps = []
    batch = wait_for_batch(client, "b", poll_interval=5, sleep=sleeps.append)
    assert batch.processing_status == "ended"
    assert sleeps == [5]


def test_wait_timeout(mocker):
    client = mocker.Mock()
    client.messages.batches.retrieve.return_value = SimpleNamespace(processing_status="in_progress")
    with pytest.raises(TimeoutError):
        wait_for_batch(client, "b", poll_interval=10, timeout=20, sleep=lambda _: None)


def _ok(custom_id):
    usage = SimpleNamespace(
        input_tokens=1_000_000,
        output_tokens=0,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        cache_creation=None,
    )
    msg = SimpleNamespace(
        model="claude-sonnet-5-5",
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text="ciao")],
        usage=usage,
    )
    return SimpleNamespace(
        custom_id=custom_id, result=SimpleNamespace(type="succeeded", message=msg)
    )


def test_collect_e_costo(mocker):
    errored = SimpleNamespace(
        custom_id="e",
        result=SimpleNamespace(
            type="errored", error=SimpleNamespace(error=SimpleNamespace(message="non valido"))
        ),
    )
    expired = SimpleNamespace(custom_id="x", result=SimpleNamespace(type="expired"))
    client = mocker.Mock()
    client.messages.batches.results.return_value = [expired, _ok("a"), errored]
    outcomes = collect_results(client, "b")
    assert outcomes["a"].text == "ciao"
    assert outcomes["e"].error == "non valido"
    assert outcomes["x"].status == "expired"
    # 1M token di input su Sonnet 5.5 = $2, con sconto batch = $1.
    assert batch_cost(outcomes) == pytest.approx(1.0)
