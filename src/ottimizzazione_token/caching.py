"""Helper per richieste cache-friendly e per verificare che il prompt caching funzioni."""

from __future__ import annotations

import copy
import re
from typing import Any, Literal

from .pricing import UsageTokens

Ttl = Literal["5m", "1h"]

# Fonte: https://platform.claude.com/docs/en/build-with-claude/prompt-caching (2026-10-15).
# Sotto queste soglie il prefisso non viene messo in cache, senza alcun errore.
MIN_CACHEABLE_TOKENS: dict[str, int] = {
    "claude-fable-5-1": 512,
    "claude-fable-5": 512,
    "claude-opus-5-5": 512,
    "claude-opus-5": 512,
    "claude-sonnet-5-5": 512,
    "claude-haiku-5-5": 512,
    "claude-opus-4-8": 1024,
    "claude-sonnet-5": 1024,
    "claude-sonnet-4-6": 1024,
    "claude-opus-4-7": 2048,
    "claude-opus-4-6": 4096,
    "claude-haiku-4-5": 4096,
}

_VOLATILE_PATTERNS = {
    "data/ora": re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?"),
    "orario": re.compile(r"\b\d{1,2}:\d{2}:\d{2}\b"),
    "UUID": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
    ),
}


def cache_control(ttl: Ttl = "5m") -> dict[str, str]:
    """
    Crea il marcatore `cache_control`.

    Args:
        ttl (Ttl): "5m" (default, scrittura x1.25) o "1h" (scrittura x2).

    Returns:
        dict[str, str]: Marcatore da mettere su un blocco di contenuto.
    """
    return {"type": "ephemeral"} if ttl == "5m" else {"type": "ephemeral", "ttl": "1h"}


def cached_system(text: str, ttl: Ttl = "5m") -> list[dict[str, Any]]:
    """
    Crea un system prompt con breakpoint di cache alla fine.

    Args:
        text (str): System prompt stabile (niente date, ID o dati per richiesta).
        ttl (Ttl): Durata della cache.

    Returns:
        list[dict[str, Any]]: Valore da passare come `system=`.
    """
    return [{"type": "text", "text": text, "cache_control": cache_control(ttl)}]


def with_cached_tools(tools: list[dict[str, Any]], ttl: Ttl = "5m") -> list[dict[str, Any]]:
    """
    Restituisce una copia dei tool con breakpoint di cache sull'ultimo.

    I tool vengono prima del system prompt, quindi la loro lista deve restare identica
    (stesso ordine, stesso contenuto) tra le richieste.

    Args:
        tools (list[dict[str, Any]]): Definizioni dei tool.
        ttl (Ttl): Durata della cache.

    Returns:
        list[dict[str, Any]]: Copia con `cache_control` sull'ultimo tool.

    Raises:
        ValueError: Se la lista è vuota.
    """
    if not tools:
        raise ValueError("Lista di tool vuota")
    result = copy.deepcopy(tools)
    result[-1]["cache_control"] = cache_control(ttl)
    return result


def min_cacheable_tokens(model: str) -> int:
    """
    Soglia minima di token perché un prefisso venga messo in cache.

    Args:
        model (str): Model ID esatto.

    Returns:
        int: Token minimi.

    Raises:
        ValueError: Se il modello non è noto.
    """
    try:
        return MIN_CACHEABLE_TOKENS[model]
    except KeyError:
        raise ValueError(f"Soglia di cache sconosciuta per {model!r}") from None


def find_volatile_content(text: str) -> list[str]:
    """
    Cerca contenuti che cambiano a ogni richiesta e invaliderebbero la cache se nel prefisso.

    Args:
        text (str): Testo destinato al prefisso in cache (tool, system).

    Returns:
        list[str]: Descrizioni dei contenuti trovati, es. "data/ora: 2026-10-15 14:00".
    """
    found = []
    for label, pattern in _VOLATILE_PATTERNS.items():
        found.extend(f"{label}: {m.group(0)}" for m in pattern.finditer(text))
    return found


def cache_hit_rate(usage: UsageTokens) -> float:
    """
    Quota del prompt servita dalla cache (0-1).

    Args:
        usage (UsageTokens): Token di una richiesta.

    Returns:
        float: Token letti dalla cache / token totali del prompt.
    """
    total = usage.prompt_tokens
    return usage.cache_read_tokens / total if total else 0.0


def diagnose_cache(usages: list[UsageTokens]) -> list[str]:
    """
    Analizza una sequenza di richieste che condividono lo stesso prefisso.

    Args:
        usages (list[UsageTokens]): Token delle richieste, in ordine di invio.

    Returns:
        list[str]: Problemi trovati; lista vuota se la cache funziona.
    """
    if len(usages) < 2:
        return ["Servono almeno 2 richieste con lo stesso prefisso per verificare la cache."]

    def writes(u: UsageTokens) -> int:
        return u.cache_write_5m_tokens + u.cache_write_1h_tokens

    if all(writes(u) == 0 and u.cache_read_tokens == 0 for u in usages):
        return [
            "Nessuna scrittura né lettura in cache: manca cache_control oppure il prefisso "
            "è sotto la soglia minima del modello."
        ]
    problems = []
    later = usages[1:]
    misses = [i for i, u in enumerate(later, start=2) if u.cache_read_tokens == 0]
    if misses:
        problems.append(
            f"Nessuna lettura dalla cache nelle richieste {misses}: il prefisso è cambiato "
            "(contenuti variabili prima del breakpoint) o la cache è scaduta."
        )
    if all(writes(u) > 0 for u in later) and all(writes(u) >= writes(usages[0]) for u in later):
        problems.append(
            "Ogni richiesta riscrive tutta la cache: il breakpoint probabilmente cade dopo "
            "contenuto diverso per ogni richiesta; spostalo alla fine della parte condivisa."
        )
    return problems
