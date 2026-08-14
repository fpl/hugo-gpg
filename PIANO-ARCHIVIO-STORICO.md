# Piano di completamento del porting di old/ sotto archivio-storico

Documento di riferimento per il lavoro ancora da fare nel recupero di
`../old/www.gruppopugliagrotte.it/` (il sito pre-WordPress) sotto
`content/archivio-storico/`. Aggiornare questo file quando una fase viene
completata o quando il censimento cambia (es. se emergono nuove pagine
durante il lavoro).

**Stato: tutte e 7 le fasi (C, A, B, D, G, E, F) sono completate.** Il piano
resta come riferimento storico delle decisioni prese fase per fase.

## Contesto

Le fasi già completate (script `old_to_hugo.py`, più parecchio lavoro manuale di
recupero) hanno portato sotto `content/archivio-storico/` circa 70 pagine: le 16
pagine di primo livello originarie, gli eventi 2003–2014 (65 pagine), i corsi
18ª–36ª, gli indici dei bollettini 1984–2008, il progetto Santo Tomás (incluse le
10 presentazioni PPT convertite in PDF) e, nell'ultimo batch, le 17 sotto-pagine di
"Esplorazione e ricerca" (Alburni, nuove cavità, Albania 2001-2004).

Un censimento di `../old/www.gruppopugliagrotte.it/` mostra che questo è solo una
parte del sito storico. Ci sono **949 pagine .htm totali**; quelle non ancora
toccate sono distribuite su una dozzina di sezioni tematiche, di dimensione molto
variabile. Questo piano le organizza in fasi eseguibili una alla volta, sul modello
delle fasi già fatte: stesso criterio di esclusione (`_eng.htm`, `*OLD*/NS`,
`sponsor/`, `cgi-bin/` vuota, media non riproducibili `.swf`/`.class`/`.wmv`,
`cd.htm`/`Statuto.htm` mai uniti a `chi-siamo/`), stesse euristiche di data già
applicate (range più vecchio, altrimenti 16 novembre + anno, altrimenti data
convenzionale), stessa attenzione a non lasciare link a icone di
navigazione/decorazione.

**Nota di stile**: molte delle pagine già migrate ripetono a mano la stessa tabella
markdown a 2 colonne per le gallerie fotografiche. Con questo volume di pagine
ancora da fare, vale la pena valutare — non necessariamente subito — uno shortcode
Hugo dedicato (`{{< gallery ... >}}`) invece di riscrivere la tabella ogni volta.
Questo si collega al punto già presente in `TODO.md` sulla validazione delle
conversioni pandoc e sulla pulizia dei layout.

## Fasi

### Fase A — Rifiniture su sezioni già migrate (~25 pagine, sforzo basso)

Pagine orfane collegate a contenuto già portato, stesso pattern già usato in
questa sessione (sotto-pagine mancanti, popup non seguiti la prima volta):

- `eventi/`: `Arrivedpresid.htm` (probabile controparte di `presidentenew.md`),
  `cuba2006.imm/inv/rel.htm` (dettagli di `cuba2006.md`), `falo2005_2..5.htm`
  (foto aggiuntive di `falo2005.md`), `speleofilm2011_2.htm` ("le impressioni di
  Valentina", linkata da `speleofilm2011.md` e mai seguita).
- `santomas/`: `aid.htm`, `francesco.htm`, `Jimenez.htm`, `scuola.htm`,
  `vinales.htm` (i popup JS di `chi.htm`/`dove.htm`/`perche.htm` lasciati come
  testo semplice), più `risultati.htm`, `contributo.htm`, `bibliografia.htm`,
  `carta.htm`, `etica.htm`, `Contatti.htm`, `news.htm` (voci del menu
  "Materiali/Contatti" mai seguite perché fuori dalla cella `class="testo"`).
- `attivi/`: `angelo.htm`, `braca.htm`, `laterza.htm`, `notarvincenzo.htm` (stesso
  genere delle pagine "nuova cavità" già fatte).

### Fase B — Pagine storiche di primo livello (~25 pagine, valore alto)

Nessuna già linkata da contenuto migrato, quindi vanno scoperte e collegate ex
novo:

- **`crono.htm`** — "La cronistoria del gruppo": probabile linea del tempo
  completa dell'associazione. Priorità alta, è mancante e non sostituibile con
  altro.
- Serie anniversario/falò mancanti agli estremi di quelle già fatte:
  `anniversario.htm` (64°, 2002), `anniversario03.htm` (65°, 2003), `falo.htm`
  (2002), `falo2003.htm`.
- `30anniphotoshow.htm` e `trentanni.htm` (30° anniversario, 2001) — naturale
  compagno di `40anni.md` già migrata.
- Racconti di viaggio/attività isolati: `frasassi.htm`, `indonesia.htm`,
  `spagna.htm`, `tunisia.htm`, `biospeleo.htm`, `soccorso.htm`, `marcia.htm`,
  `ciechi.htm`, `biagio.htm`, `progettoscuola.htm`, `scuolamateriali.htm`,
  `speleopillole.htm`.
- Bio/memoriali già presenti in `old/` ma **da verificare per sovrapposizione**
  con le pagine reali già migrate da WP (es. `/museo/chi-era-franco-anelli/`)
  prima di toccarle: `anelli.htm`, `anellichi.htm`, `orofino.htm`,
  `orofinochi.htm`, `demarzo.htm`, `mancini.htm`, `pintochi.htm`,
  `simoninichi.htm`, `faianochi.htm`.
- Corsi 1–4 (`corso.htm`, `corso2.htm`, `corso3.htm`, `corso4.htm`) + indice
  `corsi.htm`/`corsinumeri.htm`: prima delle edizioni 18ª–36ª già fatte, colmano
  l'inizio della serie storica dei corsi.
- **Esplicitamente esclusi**: `cd.htm` (Consiglio Direttivo storico) e
  `Statuto.htm`, come da regola cardine già stabilita — mai presentati come
  equivalenti alle pagine reali di `chi-siamo/`.

### Fase C — Rivista e Quaderni (18 pagine, valore alto: sblocca link già rotti)

Le pagine già migrate `archivio-storico/rivista-grotte-e-dintorni.md` e
`archivio-storico/pubblicazioni.md` elencano già questi titoli come **testo
semplice non linkato**, perché all'epoca del porting iniziale queste pagine non
erano ancora state trovate:

- `grottedin_1.htm` … `grottedin_14.htm` — i 14 numeri della rivista "Grotte e
  Dintorni" (confermato: es. `grottedin_1.htm` = "Numero 1/2001").
- `q1985.htm`, `q1986.htm`, `q1987.htm`, `q1995.htm` + `quaderni.htm` (indice) —
  i Quaderni di Speleologia Meridionale.

Priorità alta rispetto alle altre fasi: è un fix diretto di riferimenti già
visibili sul sito attuale, stesso tipo di lavoro già fatto per i bollettini/le
presentazioni.

### Fase D — Rassegna stampa (190 pagine, meccanico ma grande)

`rassegna/` è un archivio di rassegna stampa 1972–2013, organizzato per anno
(`rassegna/1972/` … `rassegna/2013/`, più `rassegna/images/<anno>/`). Ogni pagina
è nella stessa forma già gestita per Fax/Gazzetta di `cuba.md`: un wrapper minimo
attorno a un'unica immagine di ritaglio scansionato. Non serve conversione pandoc
pagina per pagina — si presta a una pagina indice per anno (o galleria unica) che
collega direttamente le immagini scansionate, sul modello già in uso.

Da decidere con l'utente: rassegna completa (tutti i 40 anni) o solo gli
anni/articoli già citati da altro contenuto migrato, come fu la scelta originale
per la Fase 1.

### Fase E — Gallerie fotografiche complete dei corsi ✅ completata

`corso/<numero>/` (23–36) contiene le gallerie fotografiche integrali e pagine di
dettaglio (es. `badino.htm`, programmi) di ogni edizione — le pagine `corsoNN.md`
già migrate ne riportano solo una selezione o un riassunto.

Migrata: 13 edizioni (23–29, 31–36; la 30 non ha pagine .htm proprie, solo
materiali in PDF ora collegati a mano in `corso30.md`) riunite ciascuna in
un'unica pagina `content/archivio-storico/corsi/<N>/archivio-fotografico.md`
(~2000 foto totali), più `programma.md` per le sole edizioni 23–25 (uniche con
un programma di corso proprio in `old/`). Script: `build_corsi_gallerie()` /
`python3 scripts/old_to_hugo.py --corsi-gallerie` in `scripts/old_to_hugo.py`.
Non tutti i file erano gallerie pure (alcuni sono resoconti narrativi di singole
uscite, es. `corso/28/1.htm`, `corso/32/pozzo.htm`): trattati con la stessa
pipeline, che rende bene entrambi i casi.

### Fase F — Testo integrale degli articoli dei bollettini ✅ completata

`bollettini/<autore>_<anno>.htm` — testo completo di singoli articoli (es.
`amatulli_2001.htm`, `comparelli_1986.htm`), oltre al solo indice già presente
nelle pagine `bollettino-YYYY.md`.

Migrati: 72 articoli (1986, 1991, 1996, 1999, 2001, 2003) sotto
`content/archivio-storico/bollettini/<anno>/`, con ogni titolo negli indici
`bollettino-<anno>.md` ora collegato alla pagina reale (prima testo semplice non
linkato). Include, per scelta esplicita dell'utente, le due pagine con l'elenco
soci (`members_2001.htm`, `2003/x.htm`). Script: `build_bollettini_testo()` +
`link_bollettini_index()` / `python3 scripts/old_to_hugo.py --bollettini-testo`.

### Fase G — Sezioni tematiche autonome mai toccate (~70 pagine)

Sezioni indipendenti, mai referenziate da contenuto già migrato, quindi da
valutare esplicitamente se rientrano nell'archivio o restano fuori scope:

- `Trek/` (20) — "Trekking", attività escursionistica collaterale.
- `didattica/` (20) — laboratori/incontri nelle scuole (`ipsiam2009.htm`,
  `angiulli.htm`, ecc.), distinta dai corsi di speleologia veri e propri.
- `GNS/` (8) — pannelli della mostra "Giornata Nazionale della Speleologia".
- `convreg/` (6) — materiale di supporto del III Convegno di Speleologia
  Pugliese.
- `ulivi/` (6) — campagna ambientale sugli ulivi secolari.
- `interviste/` (8) — perlopiù pagine frameset/indice duplicate; da verificare
  quante pagine di contenuto reale ci sono dietro.
- `soci/` (2) — `didonna.htm`, `raca.htm`, bio/memoriali di soci.
- `storia/` (1) — `ggc.htm`.

## Ordine consigliato

**C → A → B → D → G → E → F**: prima si sistemano i link già visibili e rotti (C,
A), poi le pagine di sicuro valore storico non ancora scoperte (B), poi
l'archivio stampa (D, grande ma meccanico), poi le sezioni satellite da
confermare (G), infine l'arricchimento facoltativo di corsi/bollettini (E, F) —
che non correggono nulla di rotto, solo aggiungono profondità.

## Verifica end-to-end (per ogni fase)

- `hugo --gc --minify`: 0 errori, conteggio pagine cresciuto del numero atteso.
- Grep mirato per confermare che i link della fase precedente (es. gli elenchi in
  `pubblicazioni.md`/`rivista-grotte-e-dintorni.md` per la Fase C) non puntino più
  a testo semplice non collegato.
- Controllo a vista via screenshot headless-Chrome di un campione di pagine per
  fase.
- Commit separati per fase (o per sotto-gruppo dentro una fase grande), mai un
  unico commit enorme.
