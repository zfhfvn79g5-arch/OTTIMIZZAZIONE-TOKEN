"""Interfaccia a riga di comando."""

from __future__ import annotations

from pathlib import Path

import anthropic
import typer

from .client import build_client
from .config import get_settings
from .counting import count_file
from .pricing import PRICES_UPDATED, UsageTokens, compute_cost
from .report import compare_input_tokens, format_comparison

app = typer.Typer(
    help="Misura e riduci token e costi delle chiamate a Claude.", no_args_is_help=True
)

FileArg = typer.Argument(..., exists=True, dir_okay=False, readable=True)
ModelOpt = typer.Option(None, "--model", "-m", help="Model ID (default da configurazione).")


def _fail(message: str) -> None:
    typer.echo(f"Errore: {message}", err=True)
    raise typer.Exit(code=1)


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


@app.command()
def count(
    file: Path = FileArg,
    model: str | None = ModelOpt,
    system: Path | None = typer.Option(
        None, "--system", "-s", exists=True, dir_okay=False, help="File con il system prompt."
    ),
) -> None:
    """Conta i token di un file (chiama l'endpoint gratuito count_tokens)."""
    settings = get_settings()
    model = model or settings.default_model
    try:
        system_text = system.read_text(encoding="utf-8") if system else None
        tokens = count_file(build_client(settings), file, model, system=system_text)
        cost = compute_cost(model, UsageTokens(input_tokens=tokens)).total
    except (ValueError, anthropic.APIError) as exc:
        _fail(str(exc))
    typer.echo(f"Modello: {model}")
    typer.echo(f"Token di input: {tokens:,}")
    typer.echo(f"Costo stimato come input: ${cost:.6f}")


@app.command()
def cost(
    model: str | None = ModelOpt,
    input_tokens: int = typer.Option(
        0, "--input", "-i", min=0, help="Token di input non in cache."
    ),
    output_tokens: int = typer.Option(0, "--output", "-o", min=0, help="Token di output."),
    cache_write_5m: int = typer.Option(0, "--cache-write-5m", min=0),
    cache_write_1h: int = typer.Option(0, "--cache-write-1h", min=0),
    cache_read: int = typer.Option(0, "--cache-read", min=0),
    batch: bool = typer.Option(False, "--batch", help="Message Batches API (-50%)."),
    us: bool = typer.Option(False, "--us", help="inference_geo='us' (x1.1)."),
    requests: int = typer.Option(1, "--requests", "-n", min=1, help="Moltiplica per N richieste."),
) -> None:
    """Calcola il costo di una richiesta dai suoi token (nessuna chiamata API)."""
    model = model or get_settings().default_model
    usage = UsageTokens(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_write_5m_tokens=cache_write_5m,
        cache_write_1h_tokens=cache_write_1h,
        cache_read_tokens=cache_read,
    )
    try:
        breakdown = compute_cost(model, usage, batch=batch, us_inference=us)
    except ValueError as exc:
        _fail(str(exc))
    typer.echo(f"Modello: {model} (prezzi aggiornati al {PRICES_UPDATED.isoformat()})")
    if breakdown.long_context:
        typer.echo("Prompt oltre la soglia: applicati i prezzi per contesto lungo.")
    for label, value in (
        ("Input", breakdown.input),
        ("Output", breakdown.output),
        ("Scrittura cache", breakdown.cache_write),
        ("Lettura cache", breakdown.cache_read),
    ):
        typer.echo(f"{label:<16} ${value:.6f}")
    typer.echo(f"{'Totale':<16} ${breakdown.total:.6f}")
    if requests > 1:
        typer.echo(f"Totale x {requests:,}: ${breakdown.total * requests:,.2f}")


@app.command()
def diff(
    before: Path = FileArg,
    after: Path = FileArg,
    model: str | None = ModelOpt,
    requests: int = typer.Option(1, "--requests", "-n", min=1, help="Proietta su N richieste."),
) -> None:
    """Confronta token e costo di due versioni di un prompt."""
    settings = get_settings()
    model = model or settings.default_model
    client = build_client(settings)
    try:
        comparison = compare_input_tokens(
            model, count_file(client, before, model), count_file(client, after, model)
        )
    except (ValueError, anthropic.APIError) as exc:
        _fail(str(exc))
    typer.echo(format_comparison(comparison, requests=requests))


if __name__ == "__main__":
    app()
