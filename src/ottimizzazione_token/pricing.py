"""Prezzi dei modelli Claude e calcolo del costo di una richiesta a partire da `usage`."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PRICES_UPDATED = date(2026, 10, 15)
PRICES_SOURCE = "https://platform.claude.com/docs/en/about-claude/pricing"

BATCH_DISCOUNT = 0.5
US_INFERENCE_MULTIPLIER = 1.1
_MTOK = 1_000_000


class ModelPrice(BaseModel):
    """Prezzi di un modello in USD per milione di token (API Anthropic, endpoint globale)."""

    model_config = ConfigDict(frozen=True)

    input: float
    output: float
    cache_write_5m: float
    cache_write_1h: float
    cache_read: float


class ModelPricing(BaseModel):
    """Listino di un modello, con eventuale fascia di prezzo per prompt lunghi."""

    model_config = ConfigDict(frozen=True)

    standard: ModelPrice
    long_context: ModelPrice | None = None
    long_context_threshold: int | None = None
    supports_inference_geo: bool = True


def _p(inp: float, out: float, w5: float, w1: float, read: float) -> ModelPrice:
    return ModelPrice(input=inp, output=out, cache_write_5m=w5, cache_write_1h=w1, cache_read=read)


# Motivo: unico punto in cui stanno i prezzi; aggiornare insieme a PRICES_UPDATED.
PRICES: dict[str, ModelPricing] = {
    "claude-fable-5-1": ModelPricing(standard=_p(10, 50, 12.5, 20, 0.25)),
    "claude-fable-5": ModelPricing(standard=_p(10, 50, 12.5, 20, 1)),
    "claude-opus-5-5": ModelPricing(standard=_p(4, 20, 5, 8, 0.20)),
    "claude-opus-5": ModelPricing(standard=_p(5, 25, 6.25, 10, 0.50)),
    "claude-opus-4-8": ModelPricing(standard=_p(5, 25, 6.25, 10, 0.50)),
    "claude-opus-4-7": ModelPricing(standard=_p(5, 25, 6.25, 10, 0.50)),
    "claude-opus-4-6": ModelPricing(standard=_p(5, 25, 6.25, 10, 0.50)),
    "claude-sonnet-5-5": ModelPricing(standard=_p(2, 10, 2.5, 4, 0.10)),
    "claude-sonnet-5": ModelPricing(standard=_p(2, 10, 2.5, 4, 0.20)),
    "claude-sonnet-4-6": ModelPricing(standard=_p(3, 15, 3.75, 6, 0.30)),
    "claude-haiku-5-5": ModelPricing(
        standard=_p(0.10, 0.50, 0.125, 0.20, 0.01),
        long_context=_p(0.50, 2.50, 0.625, 1, 0.05),
        long_context_threshold=100_000,
    ),
    "claude-haiku-4-5": ModelPricing(
        standard=_p(1, 5, 1.25, 2, 0.10), supports_inference_geo=False
    ),
}


class UsageTokens(BaseModel):
    """Token di una richiesta, divisi per categoria di prezzo."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_write_5m_tokens: int = Field(default=0, ge=0)
    cache_write_1h_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)

    @property
    def prompt_tokens(self) -> int:
        """Token totali del prompt: non in cache + scritti in cache + letti dalla cache."""
        return (
            self.input_tokens
            + self.cache_write_5m_tokens
            + self.cache_write_1h_tokens
            + self.cache_read_tokens
        )

    @classmethod
    def from_usage(cls, usage: Any) -> UsageTokens:
        """
        Converte l'oggetto `response.usage` dell'SDK (o un dict con gli stessi campi).

        Args:
            usage (Any): `response.usage` oppure dict equivalente.

        Returns:
            UsageTokens: Token divisi per categoria.
        """

        def get(obj: Any, name: str) -> int:
            value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
            return int(value or 0)

        cache_creation = (
            usage.get("cache_creation")
            if isinstance(usage, dict)
            else getattr(usage, "cache_creation", None)
        )
        total_write = get(usage, "cache_creation_input_tokens")
        if cache_creation is not None:
            write_5m = get(cache_creation, "ephemeral_5m_input_tokens")
            write_1h = get(cache_creation, "ephemeral_1h_input_tokens")
        else:
            # Motivo: senza dettaglio per TTL, la scrittura è quella di default a 5 minuti.
            write_5m, write_1h = total_write, 0
        return cls(
            input_tokens=get(usage, "input_tokens"),
            output_tokens=get(usage, "output_tokens"),
            cache_write_5m_tokens=write_5m,
            cache_write_1h_tokens=write_1h,
            cache_read_tokens=get(usage, "cache_read_input_tokens"),
        )


class CostBreakdown(BaseModel):
    """Costo in USD per categoria di token."""

    model: str
    input: float
    output: float
    cache_write: float
    cache_read: float
    long_context: bool = False

    @property
    def total(self) -> float:
        """Costo totale in USD."""
        return self.input + self.output + self.cache_write + self.cache_read


def get_pricing(model: str) -> ModelPricing:
    """
    Restituisce il listino di un modello.

    Args:
        model (str): Model ID esatto, es. "claude-opus-5-5".

    Returns:
        ModelPricing: Listino del modello.

    Raises:
        ValueError: Se il modello non è nel listino.
    """
    try:
        return PRICES[model]
    except KeyError:
        known = ", ".join(sorted(PRICES))
        raise ValueError(f"Modello sconosciuto: {model!r}. Modelli noti: {known}") from None


def compute_cost(
    model: str,
    usage: UsageTokens,
    *,
    batch: bool = False,
    us_inference: bool = False,
) -> CostBreakdown:
    """
    Calcola il costo di una richiesta.

    Args:
        model (str): Model ID esatto.
        usage (UsageTokens): Token della richiesta.
        batch (bool): True se inviata con la Message Batches API (-50% su tutto).
        us_inference (bool): True se inviata con `inference_geo="us"` (x1.1 su tutto).

    Returns:
        CostBreakdown: Costo per categoria.

    Raises:
        ValueError: Se il modello è sconosciuto o non supporta `inference_geo`.
    """
    pricing = get_pricing(model)
    if us_inference and not pricing.supports_inference_geo:
        raise ValueError(f"{model} non supporta inference_geo")

    long_context = (
        pricing.long_context is not None
        and pricing.long_context_threshold is not None
        and usage.prompt_tokens > pricing.long_context_threshold
    )
    price = pricing.long_context if long_context else pricing.standard
    assert price is not None

    multiplier = (BATCH_DISCOUNT if batch else 1.0) * (
        US_INFERENCE_MULTIPLIER if us_inference else 1.0
    )

    def cost(tokens: int, per_mtok: float) -> float:
        return tokens * per_mtok / _MTOK * multiplier

    return CostBreakdown(
        model=model,
        input=cost(usage.input_tokens, price.input),
        output=cost(usage.output_tokens, price.output),
        cache_write=cost(usage.cache_write_5m_tokens, price.cache_write_5m)
        + cost(usage.cache_write_1h_tokens, price.cache_write_1h),
        cache_read=cost(usage.cache_read_tokens, price.cache_read),
        long_context=long_context,
    )
