"""Interfaccia a riga di comando."""

from __future__ import annotations

import typer

from .config import get_settings

app = typer.Typer(
    help="Misura e riduci token e costi delle chiamate a Claude.", no_args_is_help=True
)


@app.callback()
def main() -> None:
    """Ottimizzazione Token."""


@app.command()
def config() -> None:
    """Mostra la configurazione attiva (senza rivelare la chiave API)."""
    settings = get_settings()
    key = "impostata" if settings.anthropic_api_key else "non impostata (uso credenziali SDK)"
    typer.echo(f"Modello di default: {settings.default_model}")
    typer.echo(f"ANTHROPIC_API_KEY: {key}")
    typer.echo(f"Retry massimi: {settings.max_retries}")
    typer.echo(f"Timeout (s): {settings.timeout}")


if __name__ == "__main__":
    app()
