# TASK – Ottimizzazione Token

## Da fare

### Fase 1 – Fondamenta (2026-10-15)
- [x] Creare `pyproject.toml`, struttura `src/ottimizzazione_token/` e `tests/`
- [x] Aggiungere `.env.example` e `.env` al `.gitignore`
- [x] `config.py`: settings pydantic (API key, modello di default)
- [x] `client.py`: wrapper attorno all'SDK `anthropic`

### Fase 2 – Misura (2026-10-15)
- [x] `counting.py`: conteggio token con `messages.count_tokens`
- [x] `pricing.py`: tabella prezzi con data di aggiornamento + costo da `response.usage` (incluse letture/scritture cache)
- [x] `report.py`: confronto prima/dopo (token, costo, risparmio %)
- [x] `cli.py`: comandi `count` e `cost`

### Fase 3 – Ottimizzazione (2026-10-15)
- [ ] `compression.py`: prime tecniche di riduzione del prompt, con test che il risultato sia più corto
- [ ] `caching.py`: helper `cache_control` + verifica `cache_read_input_tokens`
- [ ] `batching.py`: invio e lettura risultati con Message Batches API
- [ ] Confronto modelli/effort sullo stesso input (`cli.py compare`)

### Fase 4 – Validazione (2026-10-15)
- [ ] Raccogliere prompt di esempio in `examples/`
- [ ] Benchmark del risparmio per tecnica (da lanciare solo su richiesta: usa l'API reale)
- [ ] Aggiornare `README.md` con setup, uso e risparmi misurati

## Completati
- [x] Installare il template context-engineering-intro (2026-10-15)
- [x] Adattare `CLAUDE.md` al progetto (2026-10-15)
- [x] Creare `PLANNING.md` e `TASK.md` (2026-10-15)

## Scoperti durante il lavoro
- [x] `cli.py` minimale con comando `config` (serve all'entry point del pacchetto) (2026-10-15)
- [ ] Aggiungere al README le istruzioni di setup (`.venv`, `pip install -e ".[dev]"`, `.env`) (2026-10-15)
- [x] Comando `diff` per confrontare due versioni di un prompt (2026-10-15)
- [ ] Verificare `count`/`diff` contro l'API reale (count_tokens è gratuito, serve una chiave) (2026-10-15)
- [ ] Ricontrollare periodicamente i prezzi in `pricing.py` (ultimo aggiornamento 2026-10-15) (2026-10-15)
