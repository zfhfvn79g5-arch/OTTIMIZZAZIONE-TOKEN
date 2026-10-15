"""Conteggio dei token con l'endpoint `messages.count_tokens` (mai con tokenizer non Claude)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anthropic


def count_tokens(
    client: anthropic.Anthropic,
    model: str,
    messages: list[dict[str, Any]],
    *,
    system: str | list[dict[str, Any]] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> int:
    """
    Conta i token di input di una richiesta, esattamente come li conterebbe `messages.create`.

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        model (str): Model ID: i conteggi dipendono dal modello.
        messages (list[dict[str, Any]]): Messaggi della richiesta.
        system (str | list[dict[str, Any]] | None): System prompt opzionale.
        tools (list[dict[str, Any]] | None): Definizioni dei tool opzionali.

    Returns:
        int: Token di input.
    """
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if system is not None:
        kwargs["system"] = system
    if tools is not None:
        kwargs["tools"] = tools
    return client.messages.count_tokens(**kwargs).input_tokens


def count_text(
    client: anthropic.Anthropic, text: str, model: str, *, system: str | None = None
) -> int:
    """
    Conta i token di un testo inviato come singolo messaggio utente.

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        text (str): Testo da contare.
        model (str): Model ID.
        system (str | None): System prompt opzionale.

    Returns:
        int: Token di input.

    Raises:
        ValueError: Se il testo è vuoto (l'API rifiuta messaggi vuoti).
    """
    if not text.strip():
        raise ValueError("Il testo da contare è vuoto")
    return count_tokens(client, model, [{"role": "user", "content": text}], system=system)


def count_file(
    client: anthropic.Anthropic, path: str | Path, model: str, *, system: str | None = None
) -> int:
    """
    Conta i token del contenuto di un file di testo.

    Args:
        client (anthropic.Anthropic): Client Anthropic.
        path (str | Path): Percorso del file (UTF-8).
        model (str): Model ID.
        system (str | None): System prompt opzionale.

    Returns:
        int: Token di input.
    """
    return count_text(client, Path(path).read_text(encoding="utf-8"), model, system=system)
