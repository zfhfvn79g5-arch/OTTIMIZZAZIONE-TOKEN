"""Confronto di costo e risposta dello stesso prompt su modelli ed effort diversi."""

from __future__ import annotations

from typing import Any

import anthropic
from pydantic import BaseModel

from .pricing import UsageTokens, compute_cost

EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


class VariantResult(BaseModel):
    """Risultato di una combinazione modello/effort."""

    model: str
    effort: str | None
    stop_reason: str | None
    text: str
    usage: UsageTokens
    cost: float


def run_variant(
    client: anthropic.Anthropic,
    prompt: str,
    model: str,
    *,
    effort: str | None = None,
    system: str | None = None,
    max_tokens: int = 16_000,
) -> VariantResult:
    """
    Esegue il prompt su un modello. ATTENZIONE: spende token reali.

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        prompt (str): Messaggio utente.
        model (str): Model ID.
        effort (str | None): Livello di effort; None = default del modello.
        system (str | None): System prompt opzionale.
        max_tokens (int): Limite di output (include il ragionamento del modello).

    Returns:
        VariantResult: Risposta, token e costo.

    Raises:
        ValueError: Se l'effort non è valido.
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if effort is not None:
        if effort not in EFFORT_LEVELS:
            raise ValueError(f"Effort non valido: {effort!r}. Validi: {EFFORT_LEVELS}")
        kwargs["output_config"] = {"effort": effort}
    if system is not None:
        kwargs["system"] = system
    # Motivo: niente fallback automatici su altri modelli, altrimenti il confronto
    # misurerebbe un modello diverso da quello richiesto; un rifiuto resta visibile
    # come stop_reason == "refusal".
    response = client.messages.create(**kwargs)
    usage = UsageTokens.from_usage(response.usage)
    return VariantResult(
        model=model,
        effort=effort,
        stop_reason=response.stop_reason,
        text="".join(b.text for b in response.content if b.type == "text"),
        usage=usage,
        cost=compute_cost(model, usage).total,
    )


def compare_variants(
    client: anthropic.Anthropic,
    prompt: str,
    models: list[str],
    efforts: list[str | None],
    *,
    system: str | None = None,
    max_tokens: int = 16_000,
) -> list[VariantResult]:
    """
    Esegue il prompt su ogni combinazione modello x effort. ATTENZIONE: spende token reali.

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        prompt (str): Messaggio utente.
        models (list[str]): Model ID da confrontare.
        efforts (list[str | None]): Livelli di effort (None = default del modello).
        system (str | None): System prompt opzionale.
        max_tokens (int): Limite di output.

    Returns:
        list[VariantResult]: Risultati ordinati per costo crescente.
    """
    results = [
        run_variant(client, prompt, m, effort=e, system=system, max_tokens=max_tokens)
        for m in models
        for e in efforts
    ]
    return sorted(results, key=lambda r: r.cost)
