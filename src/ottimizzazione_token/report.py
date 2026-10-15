"""Confronto prima/dopo di un'ottimizzazione: token, costo e risparmio."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .pricing import UsageTokens, compute_cost


class Comparison(BaseModel):
    """Risultato del confronto tra due versioni di un prompt."""

    model: str
    tokens_before: int = Field(ge=0)
    tokens_after: int = Field(ge=0)
    cost_before: float
    cost_after: float

    @property
    def tokens_saved(self) -> int:
        """Token risparmiati (negativo se la versione nuova è più lunga)."""
        return self.tokens_before - self.tokens_after

    @property
    def saved_pct(self) -> float:
        """Risparmio percentuale sui token (0 se la versione iniziale è vuota)."""
        if self.tokens_before == 0:
            return 0.0
        return self.tokens_saved / self.tokens_before * 100

    @property
    def cost_saved(self) -> float:
        """Costo risparmiato in USD per singola richiesta."""
        return self.cost_before - self.cost_after


def compare_input_tokens(model: str, tokens_before: int, tokens_after: int) -> Comparison:
    """
    Confronta due conteggi di token di input, valutandoli al prezzo di input del modello.

    Args:
        model (str): Model ID usato per il prezzo.
        tokens_before (int): Token prima dell'ottimizzazione.
        tokens_after (int): Token dopo l'ottimizzazione.

    Returns:
        Comparison: Token e costo prima/dopo.
    """
    # Motivo: compute_cost gestisce anche le fasce di prezzo per prompt lunghi (Haiku 5.5).
    before = compute_cost(model, UsageTokens(input_tokens=tokens_before)).total
    after = compute_cost(model, UsageTokens(input_tokens=tokens_after)).total
    return Comparison(
        model=model,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        cost_before=before,
        cost_after=after,
    )


def format_comparison(comparison: Comparison, requests: int = 1) -> str:
    """
    Formatta il confronto come testo leggibile.

    Args:
        comparison (Comparison): Confronto da mostrare.
        requests (int): Numero di richieste su cui proiettare il risparmio.

    Returns:
        str: Report su più righe.
    """
    c = comparison
    lines = [
        f"Modello: {c.model}",
        f"Token prima:  {c.tokens_before:>10,}",
        f"Token dopo:   {c.tokens_after:>10,}",
        f"Risparmio:    {c.tokens_saved:>10,} token ({c.saved_pct:.1f}%)",
        f"Costo input per richiesta: ${c.cost_before:.6f} -> ${c.cost_after:.6f}",
    ]
    if requests > 1:
        lines.append(f"Risparmio su {requests:,} richieste: ${c.cost_saved * requests:,.2f}")
    return "\n".join(lines)
