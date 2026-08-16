# Nota: pulizia manuale degli artefatti pandoc nelle pagine di `archivio-storico/`

**Stato: fatto.** Le 17 pagine elencate più sotto, e in aggiunta la pagina gemella in
`content/pubblicazioni/` (vedi in fondo), sono state ripulite in una sessione
successiva a questa nota. Lasciata come riferimento storico e per il problema
correlato ancora aperto (ultima sezione).

## Il problema (risolto)

Molte pagine di `content/archivio-storico/` (e una di `content/pubblicazioni/`)
portavano ancora artefatti visibili della conversione HTML→Markdown via pandoc,
ereditati dal vecchio sito pre-WordPress (`old/www.gruppopugliagrotte.it/`):

- **Attributi HTML presentazionali pre-CSS**, rinominati da pandoc con prefisso
  `data-` perché senza equivalente Markdown: `data-border`, `data-align`, `data-valign`,
  `data-bgcolor`, `data-cellspacing`, `data-cellpadding`, `data-bordercolor`,
  `data-hspace`, `data-vspace` su `<img>` e tabelle. Zero effetto sul rendering.
- **Link "Torna su" orfani**: `[](#up "Torna su")` — link vuoto, privo di testo
  visibile. Causato da due bug distinti nella pipeline di `old_to_hugo.py` (icona
  rimossa a monte lasciando l'anchor vuoto; oppure `BACK_TO_TOP_RE` che toglieva il
  `<div>` interno ma non l'`<a>` che lo racchiudeva quando l'ordine era invertito).
- Tabelle con intestazioni a `colspan` rese come HTML grezzo pieno di attributi
  invece che come tabella Markdown pulita (solo `convegno-2007.md` e la sua pagina
  gemella in `pubblicazioni/`).
- **Bug scoperto durante la pulizia, più serio del previsto**: in
  `content/pubblicazioni/primo-convegno-regionale-di-speleologia-in-cavita-artificiali.md`
  la tabella del programma aveva contenuto multi-riga nelle celle senza `<br>` —
  sintassi GFM non valida che renderizzava con `<td></td>` **vuoti** in produzione:
  l'intero programma del convegno (nomi, orari, titoli) era invisibile ai visitatori,
  non solo esteticamente rumoroso.

## Come è stata fatta (per riferimento futuro su pattern simili)

**Nessun rilancio di `old_to_hugo.py`/`wp_to_hugo.py`** — vedi la sezione
"Tentativo fallito" più sotto per il perché. Invece:

1. Per le 15 pagine con solo attributi `data-*`/link "Torna su" orfani (pattern
   puramente meccanico, nessuna struttura da reinterpretare): script una tantum
   (mai committato, viveva nello scratchpad di sessione) che opera sul testo
   Markdown già committato — non sull'HTML pre-pandoc — con due regex: rimuove gli
   attributi presentazionali riconoscendo il prefisso `data-` già applicato da
   pandoc, e sostituisce `[](#up "...")`/`[](#top "...")` con
   `[**^ Torna su ^**](#up "Torna su")`. Verificato ovunque con
   `git diff --numstat` (inserzioni = cancellazioni, nessuna riga di contenuto
   reale toccata).
2. Per `convegno-2007.md` e la sua pagina gemella in `pubblicazioni/` (tabelle a
   colspan + `<div align="center">`, non risolvibili con semplice rimozione
   attributi): riscrittura a mano, stesso stile già usato per
   `iii-convegno-speleologia-pugliese/_index.md` — riga di intestazione a colspan
   → paragrafo in **grassetto**, poi tabella Markdown pulita a due colonne
   (Orario/Relatore); la tabella "Domenica" (celle con liste puntate, non
   esprimibile in una pipe table) → due sezioni in prosa. Verificato con un
   confronto lessicale vecchio/nuovo (script `compare_words.py`, stesso scratchpad)
   per escludere perdita di nomi/orari/luoghi, non solo con `git diff` a occhio.
3. `convegno-2007.md` aveva anche un'ancora `#up` mai definita (persa durante
   l'estrazione: l'originale `old/eventi/convegno2007.htm` aveva `<a name="up">`,
   pandoc lo scarta se vuoto) — aggiunto `<span id="up"></span>` in cima, verificato
   contro il sorgente `old/` prima di aggiungerlo (non un'invenzione).

Ogni file è stato verificato con una build Hugo pulita dopo la modifica (pagine e
alias totali invariati) prima del commit.

## Tentativo fallito: NON rilanciare gli script con `--force`

Una sessione precedente aveva provato a risolvere questo in blocco estendendo
`scripts/old_to_hugo.py:html_to_md()` con passate di pulizia generiche e
rilanciando lo script con `--force`. **Ha causato una perdita di contenuto reale**
su quasi tutti i file toccati: il contenuto committato in git era più ricco di
quanto qualunque fase dello script riesca a riprodurre (prosa scritta a mano, link
incrociati verso decine di altre pagine reali, campi `date:` in front matter),
probabilmente frutto di una fase editoriale successiva mai documentata/ritrovata.
L'incidente fu individuato via `git diff` PRIMA di committare e interamente
revertito — nessun dato perso nei fatti, ma il tentativo fu abbandonato in favore
dell'approccio "a mano, file per file" usato poi con successo (vedi sopra).

Le tre funzioni di pulizia (`strip_legacy_presentational_attrs`, `unwrap_align_divs`
generalizzata, `fix_empty_backtotop_anchors`) restano nello script: corrette e
innocue come codice, ma non vanno esercitate con un rilancio ampio finché non si
capisce da dove viene quel contenuto "fase 2" più ricco.

## Problema correlato ancora aperto: attributi mangiati in modo peggiore altrove

Durante la pulizia è emerso che il pattern `data-*` è più diffuso di quanto le 17
pagine sopra coprissero: `content/archivio-storico/bollettini/` (non solo i 2
bollettini 2001 già sistemati) ha probabilmente altre occorrenze, mai censite
sistematicamente (la ricerca originale copriva solo `archivio-storico/*.md` e
`pubblicazioni/*.md` di primo livello, non le sottocartelle `bollettini/`).

Trovato un caso peggiore, NON sistemato: `content/archivio-storico/bollettini/2001/
manghisi-pace2001.md`, riga 14 — una didascalia con un apice interno ha rotto il
parsing degli attributi HTML di pandoc, producendo attributi-spazzatura tipo
`data-giacomo="" data-tauro"="" data-(foto="" data-p.="" data-pace)"=""` invece di
un `alt=` pulito. Diverso dal semplice caso `data-border`/`data-align`: qui va
prima ricostruito cosa diceva l'`alt=` originale (probabile "... Giacomo Tauro
(foto P. Pace)") guardando il sorgente in `old/`, non solo rimosso rumore. Non
affrontato in questa sessione — da valutare se vale la pena un giro sistematico su
tutta `bollettini/` per trovare altri casi simili prima di sistemarli uno per uno.
