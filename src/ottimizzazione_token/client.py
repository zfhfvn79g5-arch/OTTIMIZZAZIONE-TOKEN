"""Punto unico di creazione del client Anthropic."""

from __future__ import annotations

import anthropic

from .config import Settings, get_settings


def build_client(settings: Settings | None = None) -> anthropic.Anthropic:
    """
    Crea un client Anthropic configurato secondo le impostazioni del progetto.

    Args:
        settings (Settings | None): Impostazioni da usare; se None vengono lette dall'ambiente.

    Returns:
        anthropic.Anthropic: Client pronto per le chiamate API.
    """
    settings = settings or get_settings()
    kwargs: dict[str, object] = {
        "max_retries": settings.max_retries,
        "timeout": settings.timeout,
    }
    # Motivo: passare api_key=None disattiverebbe la risoluzione automatica delle
    # credenziali dell'SDK (token OAuth, profili), quindi la passiamo solo se presente.
    if settings.anthropic_api_key is not None:
        kwargs["api_key"] = settings.anthropic_api_key.get_secret_value()
    return anthropic.Anthropic(**kwargs)
