# Nota: pulizia manuale degli artefatti pandoc nelle pagine di `archivio-storico/`

Task rimandato a una sessione futura, su richiesta esplicita dell'utente. Non fare
il regen via script (vedi sezione "Tentativo fallito" sotto) — va fatto pagina per
pagina, a mano.

## Il problema

Molte pagine di `content/archivio-storico/` (e almeno una di `content/pubblicazioni/`)
portano ancora artefatti visibili della conversione HTML→Markdown via pandoc, ereditati
dal vecchio sito pre-WordPress (`old/www.gruppopugliagrotte.it/`):

- **Attributi HTML presentazionali pre-CSS**, rinominati da pandoc con prefisso
  `data-` perché senza equivalente Markdown: `data-border`, `data-align`, `data-valign`,
  `data-bgcolor`, `data-cellspacing`, `data-cellpadding`, `data-bordercolor`,
  `data-hspace`, `data-vspace` su `<img>` e tabelle. Zero effetto sul rendering (nessun
  CSS del tema li interpreta) — puro rumore nel sorgente.
- **Attributi di rollover JavaScript morti** (`onMouseOver`/`onMouseOut` con
  `MM_swapImage`/`MM_swapImgRestore`, chrome Dreamweaver-era) rimasti attaccati ad
  anchor altrimenti reali.
- **Link "Torna su" orfani**: `[](#up "Torna su")` — un link vuoto, cliccabile ma privo
  di testo visibile. Causato da due bug distinti nella pipeline (vedi sotto), stesso
  sintomo in entrambi i casi.
- **Testo residuo del widget di stampa** ("Fai clic qui / per stampare la pagina"),
  frammento di uno `<script>` che il browser originale sostituiva con un'icona.
- Tabelle con intestazioni a `colspan` rese come HTML grezzo pieno di attributi invece
  che come tabella Markdown pulita.

## Pagina già sistemata (modello di riferimento)

`content/archivio-storico/iii-convegno-speleologia-pugliese/_index.md` — pulita a mano
in una sessione precedente, verificata con build Hugo reale (nessun artefatto residuo,
navigazione per ancore `#1`/`#3`/`#spelaion`/`#4`/`#5`/`#6`/`#up` ancora funzionante,
nessun dato reale perso). Usarla come riferimento per lo stile di pulizia:

- Tabelle con riga di intestazione a `colspan` (es. "Sessione Ambiente") →
  paragrafo in **grassetto** col titolo di sezione, seguito da una tabella Markdown
  pulita a 4 colonne (`Orario | Autore | Titolo | Note`), niente `data-*`.
- `<div align="...">` attorno a un titolo → tolto il wrapper, tenuto il testo (lo
  stesso trade-off già documentato per `unwrap_align_divs` nello script: l'allineamento
  non ha equivalente Markdown ed è già perso altrove nel sito per lo stesso motivo).
- Link "Torna su" ripetuti → normalizzati a un'unica forma pulita:
  `[**^ Torna su ^**](#up "Torna su")`.
- Attributi `data-*`/JS di rollover → rimossi, tenendo `width`/`height`/`alt` reali
  sugli `<img>`.

Questa pagina non è più gestita da `scripts/old_to_hugo.py` (rimossa da `PAGES`,
vedi commento nello script): una sessione precedente l'aveva ristrutturata a mano in
una sezione con sotto-pagine reali (`risultati.md`, `immagini.md`, mai prodotte dallo
script). È quindi manutenuta interamente a mano da ora in poi, coerente con la nota
in `CLAUDE.md` sulla protezione delle modifiche manuali.

## Altre pagine con lo stesso pattern (da fare)

Identificate via
`grep -rl 'data-border\|data-bgcolor\|Torna su' content/archivio-storico/*.md content/pubblicazioni/*.md`:

- `content/archivio-storico/esplorazione-e-ricerca.md`
- `content/archivio-storico/museo.md`
- `content/archivio-storico/albania.md`
- `content/archivio-storico/deposito-carrino.md`
- `content/archivio-storico/corso-alburni.md`
- `content/archivio-storico/museo-centro-documentazione.md`
- `content/archivio-storico/convegno-2007.md` (ha anche i link "Torna su" orfani)
- `content/archivio-storico/cuba.md`
- `content/archivio-storico/museo-laboratorio.md`
- `content/archivio-storico/festival-avventura.md`
- `content/archivio-storico/spelaion-2011.md`
- `content/archivio-storico/museo-percorso.md`
- `content/archivio-storico/rivista-grotte-e-dintorni.md`
- `content/archivio-storico/speleonight.md`
- `content/archivio-storico/pugliagrotte.md`
- `content/archivio-storico/bollettini/2001/quinto-nanna2001.md` (link "Torna su" orfani)
- `content/archivio-storico/bollettini/2001/montenegro-amatulli2001.md` (idem)

Fuori scope per `old_to_hugo.py`:

- `content/pubblicazioni/primo-convegno-regionale-di-speleologia-in-cavita-artificiali.md`
  ha lo stesso pattern ma è generata da `scripts/wp_to_hugo.py` (pipeline DB-driven,
  richiede il container MariaDB — vedi `CLAUDE.md`), non da `old_to_hugo.py`. Da
  affrontare separatamente, verificando prima se `wp_to_hugo.py` ha un choke-point
  pandoc analogo a `html_to_md()` da poter correggere allo stesso modo.

## Tentativo fallito: NON rilanciare lo script con `--force`

Una sessione ha già provato a risolvere questo in blocco estendendo
`scripts/old_to_hugo.py:html_to_md()` con tre passate di pulizia generiche
(`strip_legacy_presentational_attrs`, `unwrap_align_divs` generalizzata,
`fix_empty_backtotop_anchors` per i link "Torna su" orfani) e rilanciando lo script
con `--force` per applicarle. **Ha causato una perdita di contenuto reale** su quasi
tutti i file toccati: il contenuto committato in git è più ricco di quanto qualunque
fase dello script riesca a riprodurre (prosa scritta a mano, link incrociati verso
decine di altre pagine reali, campi `date:` in front matter) — probabilmente frutto
di una fase editoriale successiva mai documentata/ritrovata. Il rilancio con
`--force` ha sovrascritto tutto questo con l'output "grezzo" dello script, silenziosamente.
L'incidente è stato individuato via `git diff` PRIMA di committare e interamente
revertito con `git checkout` — nessun dato perso nei fatti, ma il tentativo è stato
abbandonato.

Le tre funzioni di pulizia restano nello script (sono corrette e innocue come codice:
si attivano solo quando lo script scrive un file), ma **non vanno esercitate con un
rilancio ampio** finché non si capisce da dove viene questo contenuto "fase 2" più
ricco e come riprodurlo. Sono comunque utili come riferimento per capire quale forma
dovrebbe avere l'HTML pulito, pagina per pagina, quando si edita a mano.

## Approccio consigliato per quando si riprende

Per ciascun file della lista sopra, **a mano**, non via script:

1. Leggere il file generato attuale e (se serve per capire la struttura originale)
   la pagina sorgente corrispondente in `old/www.gruppopugliagrotte.it/`.
2. Riscrivere solo il markup rotto (tabelle con `data-*`, div-align, link "Torna su"
   orfani, rollover JS morto, widget di stampa), **senza toccare testo, link o date
   reali** già presenti nel file.
3. `git diff` sul file per confermare che l'unica differenza sia markup/formattazione,
   non contenuto (stesso controllo fatto per `iii-convegno-speleologia-pugliese/_index.md`
   e per l'incidente descritto sopra: cercare righe di testo/link/`date:` rimosse senza
   una corrispondente riga aggiunta equivalente).
4. `hugo --gc --minify` per verificare che il sito builda senza errori dopo ogni file
   (o a gruppetti piccoli, non tutti insieme).
