"""Interfaccia a riga di comando."""

from __future__ import annotations

import json
from pathlib import Path

import anthropic
import typer

from .batching import batch_cost, build_requests, collect_results, submit_batch, wait_for_batch
from .benchmark import compare_variants
from .caching import find_volatile_content, min_cacheable_tokens
from .client import build_client
from .compression import STEPS, compress
from .config import get_settings
from .counting import count_file, count_text
from .pricing import PRICES_UPDATED, UsageTokens, compute_cost
from .report import compare_input_tokens, format_comparison

app = typer.Typer(
    help="Misura e riduci token e costi delle chiamate a Claude.", no_args_is_help=True
)

FileArg = typer.Argument(..., exists=True, dir_okay=False, readable=True)
_STEP_NAMES = ", ".join(STEPS)
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


def _confirm_spend(yes: bool) -> None:
    # Motivo: da CLAUDE.md, le operazioni che spendono soldi veri richiedono un consenso esplicito.
    if not yes:
        _fail("questo comando usa l'API a pagamento: ripeti con --yes per confermare.")


@app.command("compress")
def compress_cmd(
    file: Path = FileArg,
    output: Path | None = typer.Option(None, "--output", "-o", help="File di destinazione."),
    step: list[str] | None = typer.Option(
        None, "--step", help=f"Tecnica da applicare (ripetibile): {_STEP_NAMES}."
    ),
    count_tokens: bool = typer.Option(
        False, "--count", help="Misura i token prima/dopo con count_tokens (gratuito)."
    ),
    model: str | None = ModelOpt,
) -> None:
    """Comprime un prompt senza cambiarne il significato."""
    text = file.read_text(encoding="utf-8")
    try:
        result = compress(text, step or None)
    except ValueError as exc:
        _fail(str(exc))
    if output:
        output.write_text(result.text, encoding="utf-8")
        typer.echo(f"Scritto in {output}")
    else:
        typer.echo(result.text)
    typer.echo(
        f"Caratteri: {result.original_chars:,} -> {result.compressed_chars:,} "
        f"(-{result.chars_saved:,}), tecniche: {', '.join(result.steps)}",
        err=True,
    )
    if count_tokens:
        settings = get_settings()
        model = model or settings.default_model
        client = build_client(settings)
        try:
            before = count_text(client, text, model)
            after = count_text(client, result.text, model) if result.text.strip() else 0
        except (ValueError, anthropic.APIError) as exc:
            _fail(str(exc))
        typer.echo(format_comparison(compare_input_tokens(model, before, after)), err=True)


@app.command("cache-check")
def cache_check(
    file: Path = FileArg,
    model: str | None = ModelOpt,
) -> None:
    """Controlla se un prefisso (system/tool) è adatto alla cache."""
    settings = get_settings()
    model = model or settings.default_model
    text = file.read_text(encoding="utf-8")
    problems = [f"Contenuto variabile nel prefisso -> {v}" for v in find_volatile_content(text)]
    try:
        minimum = min_cacheable_tokens(model)
        tokens = count_text(build_client(settings), text, model)
    except (ValueError, anthropic.APIError) as exc:
        _fail(str(exc))
    typer.echo(f"Token del prefisso: {tokens:,} (minimo per la cache su {model}: {minimum:,})")
    if tokens < minimum:
        problems.append("Prefisso sotto la soglia minima: non verrà messo in cache.")
    for problem in problems:
        typer.echo(f"- {problem}")
    if problems:
        raise typer.Exit(code=1)
    typer.echo("OK: il prefisso è adatto alla cache.")


@app.command("batch-submit")
def batch_submit(
    file: Path = FileArg,
    model: str | None = ModelOpt,
    max_tokens: int = typer.Option(16_000, "--max-tokens", min=1),
    yes: bool = typer.Option(False, "--yes", help="Conferma la spesa."),
) -> None:
    """Invia un batch da un file JSONL con righe {"custom_id": ..., "prompt": ...}."""
    _confirm_spend(yes)
    model = model or get_settings().default_model
    prompts: dict[str, str] = {}
    try:
        for n, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row["custom_id"] in prompts:
                raise ValueError(f"riga {n}: custom_id duplicato {row['custom_id']!r}")
            prompts[row["custom_id"]] = row["prompt"]
        batch_id = submit_batch(
            build_client(), build_requests(prompts, model, max_tokens=max_tokens)
        )
    except (ValueError, KeyError, anthropic.APIError) as exc:
        _fail(f"{type(exc).__name__}: {exc}")
    typer.echo(f"Batch inviato: {batch_id} ({len(prompts):,} richieste)")


@app.command("batch-results")
def batch_results(
    batch_id: str,
    output: Path | None = typer.Option(None, "--output", "-o", help="Salva gli esiti in JSONL."),
    wait: bool = typer.Option(False, "--wait", help="Attende la fine del batch."),
) -> None:
    """Mostra stato, esiti e costo di un batch."""
    client = build_client()
    try:
        if wait:
            wait_for_batch(client, batch_id)
        else:
            status = client.messages.batches.retrieve(batch_id).processing_status
            if status != "ended":
                typer.echo(f"Batch ancora in corso (stato: {status}). Usa --wait per attendere.")
                return
        outcomes = collect_results(client, batch_id)
    except anthropic.APIError as exc:
        _fail(str(exc))
    counts: dict[str, int] = {}
    for o in outcomes.values():
        counts[o.status] = counts.get(o.status, 0) + 1
    typer.echo(", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    typer.echo(f"Costo (con sconto batch): ${batch_cost(outcomes):.6f}")
    if output:
        output.write_text(
            "".join(o.model_dump_json() + "\n" for o in outcomes.values()), encoding="utf-8"
        )
        typer.echo(f"Esiti salvati in {output}")


@app.command()
def compare(
    file: Path = FileArg,
    models: list[str] = typer.Option(..., "--model", "-m", help="Modello (ripetibile)."),
    efforts: list[str] | None = typer.Option(None, "--effort", "-e", help="Effort (ripetibile)."),
    max_tokens: int = typer.Option(16_000, "--max-tokens", min=1),
    yes: bool = typer.Option(False, "--yes", help="Conferma la spesa."),
) -> None:
    """Esegue lo stesso prompt su più modelli/effort e confronta i costi."""
    _confirm_spend(yes)
    prompt = file.read_text(encoding="utf-8")
    try:
        results = compare_variants(
            build_client(),
            prompt,
            models,
            list(efforts) if efforts else [None],
            max_tokens=max_tokens,
        )
    except (ValueError, anthropic.APIError) as exc:
        _fail(str(exc))
    for r in results:
        effort = r.effort or "default"
        typer.echo(
            f"\n=== {r.model} / effort {effort}: ${r.cost:.6f} "
            f"(in {r.usage.prompt_tokens:,}, out {r.usage.output_tokens:,}, "
            f"stop: {r.stop_reason}) ==="
        )
        typer.echo(r.text)


if __name__ == "__main__":
    app()
