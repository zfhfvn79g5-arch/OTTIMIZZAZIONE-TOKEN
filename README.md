# Ottimizzazione Token

Due strumenti per consumare meno con Claude, a seconda di come lo usi:

| Come usi Claude | Cosa ti serve |
|---|---|
| **In chat** (claude.ai, app) con abbonamento | 👉 [GUIDA_CHAT.md](GUIDA_CHAT.md): abitudini, istruzioni e prompt per consumare meno dei limiti di utilizzo. Niente da installare. |
| **Tramite API** (programmi che pagano a token) | 👉 La libreria Python qui sotto: conta token, calcola costi, comprime prompt, verifica la cache, usa i batch. |

---

## Libreria Python (uso via API)

### Installazione
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env   # inserisci ANTHROPIC_API_KEY
```
Senza chiave in `.env` l'SDK usa `ANTHROPIC_AUTH_TOKEN` o il profilo di `ant auth login`.

### Comandi
| Comando | Cosa fa | Costo |
|---|---|---|
| `ottimizzazione-token config` | mostra la configurazione | — |
| `ottimizzazione-token count prompt.txt` | conta i token di un file | gratuito |
| `ottimizzazione-token cost -m claude-sonnet-5-5 -i 2000 -o 500 -n 10000` | calcola il costo dai token | nessuna chiamata |
| `ottimizzazione-token diff prima.txt dopo.txt` | confronta due versioni di un prompt | gratuito |
| `ottimizzazione-token compress prompt.txt -o corto.txt --count` | comprime un prompt senza cambiarne il senso | gratuito |
| `ottimizzazione-token cache-check system.txt -m claude-opus-5-5` | verifica se il prefisso è adatto alla cache | gratuito |
| `ottimizzazione-token batch-submit prompts.jsonl --yes` | invia un batch (-50%) | **a pagamento** |
| `ottimizzazione-token batch-results ID --wait` | esiti e costo di un batch | — |
| `ottimizzazione-token compare prompt.txt -m modello1 -m modello2 -e low --yes` | stesso prompt su più modelli/effort | **a pagamento** |

I comandi gratuiti usano solo l'endpoint `count_tokens`. Quelli a pagamento richiedono `--yes`.

### Uso da codice
```python
from ottimizzazione_token.client import build_client
from ottimizzazione_token.counting import count_text
from ottimizzazione_token.compression import compress
from ottimizzazione_token.report import compare_input_tokens, format_comparison

client = build_client()
testo = open("prompt.txt", encoding="utf-8").read()
corto = compress(testo).text
modello = "claude-opus-5-5"
print(format_comparison(compare_input_tokens(
    modello, count_text(client, testo, modello), count_text(client, corto, modello)
)))
```

### Test
```bash
.venv/bin/pytest
.venv/bin/ruff check src tests && .venv/bin/black --check src tests
```

### Note
- I prezzi sono in `src/ottimizzazione_token/pricing.py` con la data di aggiornamento: ricontrollali sulla [pagina prezzi](https://platform.claude.com/docs/en/about-claude/pricing).
- Architettura e piano di lavoro: [PLANNING.md](PLANNING.md), [TASK.md](TASK.md). Regole per Claude Code: [CLAUDE.md](CLAUDE.md).
- Il progetto parte dal template [context-engineering-intro](https://github.com/coleam00/context-engineering-intro); il suo README originale è in [TEMPLATE_README.md](TEMPLATE_README.md).
