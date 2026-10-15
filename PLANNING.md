# PLANNING – Ottimizzazione Token

## Obiettivo
Una libreria Python (con CLI minimale) che aiuta a ridurre token e costi delle chiamate a Claude
senza peggiorare la qualità delle risposte. Ogni funzionalità deve poter mostrare un risparmio misurato.

## Ambito
Il progetto ha due parti: la libreria per l'uso via API e `GUIDA_CHAT.md` per chi usa Claude in chat con abbonamento (limiti di utilizzo, non costo a token).

**Dentro:**
- Conteggio token accurato via API (`messages.count_tokens`).
- Calcolo del costo di una richiesta/risposta a partire da `response.usage`.
- Compressione/pulizia dei prompt (spazi, duplicati, contenuto irrilevante).
- Costruzione di richieste cache-friendly e verifica del cache hit.
- Confronto modelli/effort sullo stesso input (costo vs qualità).
- Invio di lavori non urgenti tramite Message Batches API.

**Fuori (per ora):**
- Altri provider (OpenAI, Gemini…): solo se serviranno, dietro un'interfaccia separata.
- Interfaccia web/dashboard.

## Architettura
```
src/ottimizzazione_token/
├── __init__.py
├── config.py        # Settings pydantic: API key da .env, modello di default
├── client.py        # Wrapper unico attorno ad anthropic.Anthropic
├── counting.py      # Conteggio token (count_tokens)
├── pricing.py       # Tabella prezzi (con data di aggiornamento) e calcolo costi da usage
├── compression.py   # Tecniche di riduzione del prompt
├── caching.py       # Helper per cache_control e verifica cache_read_input_tokens
├── batching.py      # Creazione, polling e lettura risultati dei batch
├── report.py        # Confronto prima/dopo: token, costo, risparmio %
├── benchmark.py     # Stesso prompt su più modelli/effort: costo e risposta
└── cli.py           # Comandi: config, count, cost, diff, compress, cache-check,
                     #          batch-submit, batch-results, compare
tests/               # Rispecchia src/, con mock dell'SDK
examples/            # Prompt e richieste di esempio per test e benchmark
```

Flusso tipico: prompt → `compression` → `counting` (prima/dopo) → `client` → `usage` → `pricing` → `report`.

## Stack
- Python ≥ 3.10, virtualenv `.venv`
- `anthropic` (SDK ufficiale), `pydantic` + `pydantic-settings`, `python-dotenv`
- CLI: `typer`
- Test: `pytest`, `pytest-mock`
- Qualità: `black`, `ruff`
- Packaging: `pyproject.toml`

## Convenzioni
- Modello di default configurabile in `config.py`; solo model ID esatti dalla documentazione Anthropic.
- Prezzi in un solo posto (`pricing.py`), con data dell'ultimo aggiornamento.
- Nessuna chiamata API reale nei test unitari; benchmark/eval reali solo su richiesta esplicita.
- Ogni tecnica di ottimizzazione ha: test di correttezza, misura del risparmio, nota nel README.

## Vincoli
- La qualità dell'output non deve peggiorare: i downgrade (modello/effort/compressione) vanno validati su esempi.
- `ANTHROPIC_API_KEY` solo in `.env` (ignorato da git).
- File sotto le 500 righe.

## Metriche di successo
- Risparmio % di token e di costo per tecnica, misurato su `examples/`.
- Cache hit rate (`cache_read_input_tokens` / input totali) sulle richieste ripetute.
