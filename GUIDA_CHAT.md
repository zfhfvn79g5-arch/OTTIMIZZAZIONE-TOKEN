# Guida: consumare meno nelle chat di Claude

Questa guida è per chi usa Claude **in chat** (claude.ai, app desktop o mobile) con un abbonamento.
Lì non si paga a token ma ci sono **limiti di utilizzo**: più "pesanti" sono le conversazioni,
prima li raggiungi. Non serve installare niente: conta solo *come* usi la chat.

> Per l'uso tramite API (programmi che chiamano Claude e pagano a token) vedi invece la libreria
> Python in questo repository e il [README](README.md).

## Perché si consuma

A ogni nuovo messaggio Claude rilegge **tutta la conversazione**: i tuoi messaggi, le sue risposte,
i file allegati. Quindi:

- una chat lunga costa sempre di più, messaggio dopo messaggio;
- un file grande allegato all'inizio "pesa" su ogni risposta successiva;
- i modelli più potenti e le funzioni extra (ragionamento esteso, ricerca web) consumano di più.

## Le 10 abitudini che fanno più differenza

1. **Una chat per argomento.** Quando cambi argomento, apri una chat nuova invece di continuare quella vecchia.
2. **Chat lunga? Riparti con un riassunto.** Chiedi: *"Riassumi in 10 righe i punti decisi finora"*, copia il riassunto in una chat nuova e continua da lì.
3. **Tutto in un messaggio.** Meglio una richiesta completa (contesto + cosa vuoi + formato) che tanti messaggi piccoli di aggiustamento.
4. **Modifica invece di aggiungere.** Se Claude ha capito male, usa *modifica* sul tuo messaggio precedente invece di scrivere "no, intendevo…": la conversazione non si allunga.
5. **Allega solo ciò che serve.** Se ti serve un capitolo, incolla il capitolo, non l'intero PDF.
6. **Usa i Progetti per i materiali ricorrenti.** Se lavori spesso sugli stessi documenti, mettili in un Progetto invece di ricaricarli in ogni chat.
7. **Scegli il modello giusto.** Haiku o Sonnet per domande semplici, riassunti, traduzioni, email; Opus solo per i lavori davvero complessi.
8. **Accendi gli extra solo quando servono.** Ragionamento esteso e ricerca web sono utili, ma consumano: lasciali spenti per le domande semplici.
9. **Chiedi risposte brevi.** *"Rispondi in massimo 5 righe"* o *"solo il codice, senza spiegazioni"*.
10. **Evita di farti riscrivere tutto.** Chiedi *"mostrami solo la parte modificata"* invece del documento o del codice completo.

## Istruzioni da incollare nelle preferenze

In **Impostazioni → Profilo** (preferenze personali) puoi dare a Claude istruzioni valide per tutte
le chat. Un esempio da copiare e adattare:

```text
Rispondi in modo conciso e diretto, senza introduzioni né riepiloghi finali.
Non ripetere la mia domanda.
Quando modifichi un testo o del codice, mostra solo le parti cambiate, salvo che chieda la versione completa.
Usa elenchi puntati solo quando aiutano davvero.
Se la richiesta è ambigua, fai una sola domanda di chiarimento prima di rispondere a lungo.
```

Puoi anche scegliere lo **stile di risposta conciso** dal menu degli stili, quando disponibile.

## Skill "risparmio-token"

In [`skills/risparmio-token/`](skills/risparmio-token/SKILL.md) c'è una skill che fa applicare a Claude
queste regole da solo quando la chat si allunga o chiedi di risparmiare. Si carica su claude.ai
(piani a pagamento) caricando il file `skills/risparmio-token.zip` dalla sezione Skills delle impostazioni.
Non è sempre attiva: per le regole valide in ogni chat usa le preferenze qui sopra.

## Modelli di prompt efficienti

**Richiesta completa in un colpo solo**
```text
Contesto: [chi sei / a cosa serve].
Compito: [cosa deve fare Claude].
Vincoli: [lunghezza, tono, cosa evitare].
Formato: [elenco / tabella / email / solo codice].
```

**Ripartire da una chat lunga**
```text
Riassumi questa conversazione in massimo 10 righe: obiettivo, decisioni prese,
punti ancora aperti. Lo userò per continuare in una nuova chat.
```

**Correggere senza riscrivere tutto**
```text
Correggi solo [la parte X]. Mostrami esclusivamente le righe modificate.
```

## Se usi Claude Code

- Tieni `CLAUDE.md` breve: viene letto a ogni sessione.
- Usa `/clear` quando passi a un lavoro diverso, `/compact` quando la sessione è lunga ma vuoi continuare.
- Indica file e cartelle precisi invece di chiedere di "guardare tutto il progetto".
