# CLAUDE.md – Ottimizzazione Token

Strumenti Python per ridurre token e costi delle chiamate LLM senza peggiorare la qualità delle risposte:
conteggio token, compressione dei prompt, prompt caching, scelta di modello ed effort, batch.
Provider principale: Anthropic (Claude), tramite SDK ufficiale `anthropic`.

### 🔄 Contesto del progetto
- **Leggi `PLANNING.md`** (architettura, obiettivi, vincoli) all'inizio di ogni nuova conversazione. Se non esiste, proponi di crearlo.
- **Controlla `TASK.md`** prima di iniziare un task. Se il task non c'è, aggiungilo con una breve descrizione e la data di oggi.
- Segui naming, struttura dei file e pattern descritti in `PLANNING.md`.
- Usa il virtualenv `.venv` per ogni comando Python, test compresi.

### 💰 Regole sui token e sui costi (il cuore del progetto)
- **Conta i token con l'API, mai stimarli.** Usa `client.messages.count_tokens(model=..., messages=...)` con lo stesso modello usato in produzione. **Non usare `tiktoken`** o altri tokenizer non Claude: sottostimano i token di Claude.
- **Ogni ottimizzazione va misurata**: token e costo prima/dopo, su input reali o realistici. Niente "dovrebbe risparmiare" senza numeri.
- **Il risparmio non deve abbassare la qualità**: ogni tecnica di compressione o downgrade di modello/effort ha un test o un eval che confronta l'output con la baseline.
- **Prompt caching**: contenuto stabile in testa (tool → system → messages), parti variabili (timestamp, ID, domanda dell'utente) dopo l'ultimo `cache_control`. Verifica con `usage.cache_read_input_tokens`: se resta 0 su richieste ripetute, qualcosa invalida la cache (es. `datetime.now()` nel system prompt, JSON non ordinato, lista di tool che cambia).
- **Leggi i costi da `response.usage`** (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`), non ricalcolarli a mano dal testo.
- **Prezzi e limiti dei modelli non vanno scritti a mano nel codice sparso**: tienili in un unico modulo di configurazione con la data di aggiornamento; per context window e capacità usa la Models API (`client.models.retrieve`).
- **Ordine delle leve**: prima quelle gratuite (caching, togliere contenuto inutile dal prompt, limitare output, Batch API −50% per lavori non urgenti), poi i compromessi (effort più basso, modello più piccolo). Valuta il costo per task completato, non per singola richiesta.
- **Non usare model ID inventati o con suffissi di data**: solo ID esatti presenti nella documentazione Anthropic.
- **Nessuna chiamata API reale nei test unitari**: usa mock. Script che spendono soldi veri (benchmark, eval) vanno lanciati solo su richiesta esplicita.

### 🧱 Struttura del codice
- **Nessun file oltre le 500 righe.** Se ci si avvicina, dividi in moduli.
- Moduli separati per responsabilità, ad esempio:
  - `counting.py` – conteggio token
  - `compression.py` – riduzione/compressione dei prompt
  - `caching.py` – costruzione di richieste cache-friendly
  - `pricing.py` – prezzi e calcolo costi
  - `client.py` – wrapper unico attorno all'SDK `anthropic`
- Import relativi all'interno del package.
- Variabili d'ambiente con `python-dotenv` (`load_dotenv()`); `ANTHROPIC_API_KEY` solo in `.env`, mai nel codice o nei commit.

### 🧪 Test e affidabilità
- **Test Pytest per ogni nuova funzionalità**, nella cartella `/tests` che rispecchia la struttura del package. Per ognuna almeno: 1 caso normale, 1 caso limite, 1 caso di errore.
- Quando modifichi la logica, aggiorna i test esistenti che ne dipendono.
- Per le funzioni di ottimizzazione, testa anche che il risultato sia davvero più corto/economico dell'input.

### ✅ Completamento dei task
- Segna i task completati in `TASK.md` appena finiti.
- Sotto-task o TODO scoperti durante il lavoro vanno in `TASK.md`, sezione "Scoperti durante il lavoro".

### 📎 Stile e convenzioni
- **Python** come linguaggio principale, PEP8, type hints, formattazione con `black`, lint con `ruff`.
- **`pydantic`** per validare dati e configurazioni.
- `FastAPI` solo se serve esporre un'API.
- Docstring in stile Google per ogni funzione:
  ```python
  def esempio(param1: int) -> str:
      """
      Breve descrizione.

      Args:
          param1 (int): Descrizione.

      Returns:
          str: Descrizione.
      """
  ```

### 📚 Documentazione
- Aggiorna `README.md` quando aggiungi funzionalità, cambi dipendenze o passi di setup.
- Commenta il codice non ovvio; per la logica complessa aggiungi un commento `# Motivo:` che spieghi il perché.
- Quando una tecnica di ottimizzazione viene aggiunta, documenta nel README il risparmio misurato e su quali input.

### 🧠 Comportamento dell'AI
- **Non dare per scontato il contesto mancante: chiedi se non sei sicuro.**
- **Non inventare librerie, funzioni o parametri dell'API**: usa solo pacchetti verificati e la documentazione ufficiale Anthropic.
- Verifica che percorsi e moduli esistano prima di citarli nel codice o nei test.
- Non cancellare o sovrascrivere codice esistente se non richiesto esplicitamente o previsto da un task in `TASK.md`.
- Tieni corti i tuoi messaggi e i file di contesto: anche questo progetto deve consumare pochi token.
