"""Tecniche deterministiche di riduzione del prompt che non cambiano il significato del testo."""

from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel

# Motivo: dentro i blocchi di codice spazi e righe ripetute possono avere significato,
# quindi le trasformazioni si applicano solo alla prosa fuori dai blocchi ```.
_FENCE_RE = re.compile(r"(```.*?```)", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_INNER_SPACES_RE = re.compile(r"(?<=\S)[ \t]{2,}")
_BLANK_LINES_RE = re.compile(r"\n[ \t]*\n(?:[ \t]*\n)+")
# Motivo: paragrafi brevi ripetuti ("Esempio:", "---", "Input:") di solito strutturano
# il prompt (es. few-shot); si rimuovono solo i duplicati abbastanza lunghi.
MIN_DUPLICATE_CHARS = 40


class CompressionResult(BaseModel):
    """Testo compresso con le statistiche della compressione."""

    text: str
    original_chars: int
    compressed_chars: int
    steps: list[str]

    @property
    def chars_saved(self) -> int:
        """Caratteri rimossi."""
        return self.original_chars - self.compressed_chars


def _map_prose(text: str, func: Callable[[str], str]) -> str:
    """Applica `func` ai soli segmenti fuori dai blocchi di codice."""
    parts = _FENCE_RE.split(text)
    return "".join(part if i % 2 else func(part) for i, part in enumerate(parts))


def normalize_whitespace(text: str) -> str:
    """
    Rimuove spazi finali, comprime spazi multipli interni e righe vuote consecutive.

    L'indentazione a inizio riga viene mantenuta (liste, YAML, citazioni).

    Args:
        text (str): Testo di partenza.

    Returns:
        str: Testo normalizzato.
    """

    def clean(segment: str) -> str:
        lines = [_INNER_SPACES_RE.sub(" ", line.rstrip()) for line in segment.split("\n")]
        return _BLANK_LINES_RE.sub("\n\n", "\n".join(lines))

    return _map_prose(text.replace("\r\n", "\n"), clean).strip()


def remove_html_comments(text: str) -> str:
    """
    Rimuove i commenti HTML `<!-- ... -->`, che il modello legge ma che di solito non servono.

    Args:
        text (str): Testo di partenza.

    Returns:
        str: Testo senza commenti HTML (fuori dai blocchi di codice).
    """
    return _map_prose(text, lambda s: _HTML_COMMENT_RE.sub("", s))


def remove_duplicate_paragraphs(text: str) -> str:
    """
    Elimina i paragrafi identici ripetuti, mantenendo la prima occorrenza.

    Il confronto ignora maiuscole e spazi; i blocchi di codice e i paragrafi più corti di
    `MIN_DUPLICATE_CHARS` caratteri (titoli, separatori) non vengono toccati.

    Args:
        text (str): Testo di partenza.

    Returns:
        str: Testo senza paragrafi duplicati.
    """
    seen: set[str] = set()

    def dedupe(segment: str) -> str:
        kept = []
        for paragraph in re.split(r"(\n[ \t]*\n)", segment):
            key = " ".join(paragraph.split()).lower()
            if len(key) >= MIN_DUPLICATE_CHARS:
                if key in seen:
                    continue
                seen.add(key)
            kept.append(paragraph)
        # Motivo: rimuovere un paragrafo lascia due separatori vicini; li riduce a uno.
        return _BLANK_LINES_RE.sub("\n\n", "".join(kept))

    return _map_prose(text, dedupe)


STEPS: dict[str, Callable[[str], str]] = {
    "html_comments": remove_html_comments,
    "duplicate_paragraphs": remove_duplicate_paragraphs,
    "whitespace": normalize_whitespace,
}


def compress(text: str, steps: list[str] | None = None) -> CompressionResult:
    """
    Applica in ordine le tecniche di compressione richieste.

    Args:
        text (str): Testo di partenza.
        steps (list[str] | None): Nomi delle tecniche (chiavi di `STEPS`); None = tutte.

    Returns:
        CompressionResult: Testo compresso e statistiche.

    Raises:
        ValueError: Se una tecnica non esiste.
    """
    steps = list(STEPS) if steps is None else steps
    unknown = [s for s in steps if s not in STEPS]
    if unknown:
        raise ValueError(f"Tecniche sconosciute: {unknown}. Disponibili: {list(STEPS)}")
    result = text
    for name in steps:
        result = STEPS[name](result)
    return CompressionResult(
        text=result, original_chars=len(text), compressed_chars=len(result), steps=steps
    )
