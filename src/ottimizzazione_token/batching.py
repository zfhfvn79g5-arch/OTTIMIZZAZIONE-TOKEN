"""Invio di lavori non urgenti con la Message Batches API (-50% su tutti i token)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Literal

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from pydantic import BaseModel

from .pricing import UsageTokens, compute_cost

MAX_BATCH_REQUESTS = 100_000


class BatchOutcome(BaseModel):
    """Esito di una singola richiesta del batch."""

    custom_id: str
    status: Literal["succeeded", "errored", "canceled", "expired"]
    model: str | None = None
    text: str = ""
    usage: UsageTokens | None = None
    error: str | None = None


def build_requests(
    prompts: dict[str, str],
    model: str,
    *,
    max_tokens: int = 16_000,
    system: str | list[dict[str, Any]] | None = None,
) -> list[Request]:
    """
    Crea le richieste del batch, una per prompt.

    Args:
        prompts (dict[str, str]): custom_id -> testo del messaggio utente.
        model (str): Model ID.
        max_tokens (int): Limite di output per richiesta.
        system (str | list[dict[str, Any]] | None): System prompt condiviso (meglio se in cache).

    Returns:
        list[Request]: Richieste pronte per `submit_batch`.

    Raises:
        ValueError: Se non ci sono prompt o sono troppi.
    """
    if not prompts:
        raise ValueError("Nessun prompt da inviare")
    if len(prompts) > MAX_BATCH_REQUESTS:
        raise ValueError(f"Massimo {MAX_BATCH_REQUESTS:,} richieste per batch")
    requests = []
    for custom_id, prompt in prompts.items():
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system is not None:
            params["system"] = system
        requests.append(
            Request(custom_id=custom_id, params=MessageCreateParamsNonStreaming(**params))
        )
    return requests


def submit_batch(client: anthropic.Anthropic, requests: list[Request]) -> str:
    """
    Invia il batch. ATTENZIONE: spende token reali.

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        requests (list[Request]): Richieste da `build_requests`.

    Returns:
        str: ID del batch.
    """
    return client.messages.batches.create(requests=requests).id


def wait_for_batch(
    client: anthropic.Anthropic,
    batch_id: str,
    *,
    poll_interval: float = 60.0,
    timeout: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """
    Attende la fine del batch (di solito meno di un'ora, al massimo 24).

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        batch_id (str): ID del batch.
        poll_interval (float): Secondi tra un controllo e l'altro.
        timeout (float | None): Secondi massimi di attesa; None = nessun limite.
        sleep (Callable[[float], None]): Funzione di attesa (sostituibile nei test).

    Returns:
        Any: Oggetto batch con `processing_status == "ended"`.

    Raises:
        TimeoutError: Se il batch non finisce entro `timeout`.
    """
    waited = 0.0
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return batch
        if timeout is not None and waited >= timeout:
            raise TimeoutError(f"Batch {batch_id} non terminato dopo {waited:.0f}s")
        sleep(poll_interval)
        waited += poll_interval


def collect_results(client: anthropic.Anthropic, batch_id: str) -> dict[str, BatchOutcome]:
    """
    Legge i risultati di un batch terminato.

    I risultati arrivano in ordine qualsiasi: vanno sempre associati per custom_id.

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        batch_id (str): ID del batch.

    Returns:
        dict[str, BatchOutcome]: custom_id -> esito.
    """
    outcomes: dict[str, BatchOutcome] = {}
    for item in client.messages.batches.results(batch_id):
        result = item.result
        if result.type == "succeeded":
            msg = result.message
            outcomes[item.custom_id] = BatchOutcome(
                custom_id=item.custom_id,
                status="succeeded",
                model=msg.model,
                text="".join(b.text for b in msg.content if b.type == "text"),
                usage=UsageTokens.from_usage(msg.usage),
            )
        else:
            error = None
            if result.type == "errored":
                error = getattr(getattr(result.error, "error", None), "message", None) or str(
                    result.error
                )
            outcomes[item.custom_id] = BatchOutcome(
                custom_id=item.custom_id, status=result.type, error=error
            )
    return outcomes


def batch_cost(outcomes: dict[str, BatchOutcome]) -> float:
    """
    Costo totale in USD delle richieste riuscite, con lo sconto batch applicato.

    Args:
        outcomes (dict[str, BatchOutcome]): Esiti da `collect_results`.

    Returns:
        float: Costo totale.
    """
    return sum(
        compute_cost(o.model, o.usage, batch=True).total
        for o in outcomes.values()
        if o.status == "succeeded" and o.model and o.usage
    )
