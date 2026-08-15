# Come è stata fatta: cronaca della migrazione gruppopugliagrotte.it → Hugo

**Istantanea al 15 agosto 2026.** Il lavoro di migrazione è tuttora in corso: questo
documento fotografa lo stato e la cronologia delle attività fino a questa data e non
viene aggiornato retroattivamente a ogni modifica successiva — per lo stato più recente
del contenuto e della struttura fare sempre riferimento a `README.md` e alla cronologia
git.

Questo documento racconta, in ordine cronologico, tutto il lavoro svolto per migrare
**gruppopugliagrotte.it** (sito dell'associazione di speleologia Gruppo Puglia Grotte,
Castellana Grotte, Bari) da WordPress a Hugo. È un resoconto di attività, non una guida
tecnica: per i dettagli tecnici e le convenzioni da rispettare vedi `CLAUDE.md`; per lo
stato attuale, la struttura del contenuto e i comandi operativi vedi `README.md`.

## 1. Il punto di partenza: uno scaffold "indovinato"

La primissima versione del sito Hugo (commit iniziali) è stata costruita **senza accesso
al sito live** (bloccato da `robots.txt`) e senza database: menu, sidebar e colore
dell'header erano ricostruiti indovinando da snippet di ricerca generici sul tema
WordPress "Twenty Thirteen". Le pagine per cui non era possibile recuperare fatti reali
(nominativi del Consiglio Direttivo, testo dello statuto) erano lasciate esplicitamente
vuote con un commento `<!-- TODO migrazione -->`, seguendo fin da subito la regola più
importante di tutto il progetto: **mai inventare contenuto istituzionale**.

## 2. Da scaffold indovinato a contenuto reale: il dump del database

Il salto di qualità decisivo è arrivato quando sono state rese disponibili due fonti
autentiche:

- `../home/` — copia completa dell'installazione WordPress, inclusi `wp-content/uploads/`
  (250MB di allegati), il tema `twentythirteen/` (con i font Genericons) e i plugin
  installati.
- `../backup_*-db` — dump SQL completo del database (formato UpdraftPlus/mysqldump).

Il dump è stato importato in un container MariaDB locale (`docker`, che su questa macchina
è un alias di `podman`) e interrogato direttamente via `mysql` — niente parsing di export
WXR né di dati PHP-serialize a mano. Da questa fonte è nato lo script
`scripts/wp_to_hugo.py` (stdlib Python + `pandoc`, senza dipendenze pip), che genera tutto
`content/` a partire dal DB: pagine, i 28 post reali del blog, categorie, allegati
effettivamente referenziati nel contenuto (122 su 140 totali), riscrittura dei link interni
assoluti verso il vecchio dominio.

Con questa fonte reale sono stati sostituiti tutti gli elementi indovinati:

| Elemento | Prima | Ora |
|---|---|---|
| Colore testo header | bianco (ipotesi) | `#f4f3bc`, dal DB |
| Menu di navigazione | ricostruito da snippet | ricostruito da `wp_posts`/`wp_postmeta`, inclusa la sezione "Ambiente" mancante prima |
| Sidebar | box inventati | widget reali: Articoli recenti, Archivi (per anno), Categorie, Copyright |
| Genericons | dichiarati ma assenti | copiati dal tema WordPress reale |
| Statuto / Consiglio Direttivo | placeholder | testo integrale reale dal DB |

Decisioni non ovvie prese in questa fase, tutte documentate in `CLAUDE.md`:

- I post reali del blog vanno in `content/novita/`, non in `content/eventi/`: nel DB la
  voce di menu "Eventi" punta a una pagina statica "evergreen", distinta dallo stream di
  post mostrato in home.
- "La nostra storia" non è contenuto separato: è la stessa pagina "Chi siamo" con
  un'etichetta di menu diversa; voce rimossa dal menu su decisione dell'utente.
- Il custom post type `banner` (un solo sponsor pubblicitario storico) non è stato
  migrato: cruft non istituzionale.
- Due pagine (`Ambiente`, `Cavità artificiali`) generano un placeholder esplicito perché
  il DB conferma che sono vuote anche sul sito originale — non riempite con testo
  plausibile.

Una nota tecnica emersa durante lo sviluppo dello script: la CLI `mysql -N -B` in
modalità batch **escapa** `\t`, `\n`, `\\` e NUL nei campi, ma **non** `\r` — alcuni
contenuti reali hanno `\r` non escapato che, letto con la traduzione universal-newline di
Python, si trasformava in un ritorno a capo vero e rompeva il parsing riga-per-riga
dell'output tabulare. Risolto leggendo lo stdout come byte grezzi.

## 3. Rifiniture sul contenuto WordPress migrato

Con lo scaffold ormai basato su dati reali, il lavoro è proseguito con una serie di
correzioni mirate:

- Pulizia dell'HTML residuo lasciato da pandoc in alcuni documenti Markdown, e
  normalizzazione di ancore/immagini scritte come HTML grezzo in sintassi Markdown pulita.
- Aggiunta del Codice Fiscale alla sezione Copyright e correzione di un'immagine
  incorporata.
- Tracciamento di `.link-rewrite.json` (l'export della mappa `LINK_REWRITE` prodotta da
  `old_to_hugo.py`, vedi sezione 4) perché `wp_to_hugo.py` la legge per risolvere i link
  assoluti al vecchio dominio che puntano fuori da `/home/`.
- Un nuovo rilancio degli script di conversione per ripulire automaticamente altri link
  esterni ormai obsoleti.

## 4. L'archivio storico: il sito pre-WordPress (1999–2014)

Oltre al sito WordPress, gruppopugliagrotte.it ha avuto una vita precedente come sito
statico fatto a mano (Dreamweaver, layout a tabelle, codifica ISO-8859-1). Una copia
completa (`../old/www.gruppopugliagrotte.it/`, **949 pagine .htm**, 736MB) è stata fornita
dall'utente. Diverse di quelle pagine erano ancora citate — con URL assoluti oggi rotti —
da contenuto reale già migrato (es. `storiagpg.htm`, `museo.htm`, PDF sotto
`esplorazioni/alburni/`).

Per questo materiale è stato scritto un secondo script indipendente,
`scripts/old_to_hugo.py` (stesso vincolo "niente pip" di `wp_to_hugo.py`, nessun bisogno
del container MariaDB perché sono file statici), che scrive **solo** sotto
`content/archivio-storico/` e non tocca mai il contenuto WordPress.

Il recupero di questo archivio è stato pianificato in un documento dedicato,
`PIANO-ARCHIVIO-STORICO.md`, organizzato in **sette fasi** (di cui le prime due, "Fase 1"
e "Fase 2", erano già in corso quando il piano è stato scritto; le successive, C-A-B-D-G-E-F,
sono state definite lì e poi eseguite in quell'ordine):

- **Fase 1** (`old_to_hugo.py`, `main()`): le 16 pagine/asset di primo livello citati da
  link reali già migrati, convertite in Markdown vero con i link riscritti ai nuovi
  permalink Hugo.
- **Fase 2** (`--extend`): cronaca eventi 2003–2014 (69 pagine) e le edizioni 18ª–36ª del
  corso di speleologia (19 pagine), organizzate come sottosezioni dedicate su richiesta
  esplicita dell'utente.
- **Fase C — Rivista e Quaderni** (18 pagine, priorità alta perché sblocca link già
  visibili ma non cliccabili): i 14 numeri della rivista "Grotte e Dintorni" e 4 numeri
  dei Quaderni di Speleologia Meridionale, già elencati come testo semplice nelle pagine
  `rivista-grotte-e-dintorni.md` e `pubblicazioni.md` fin dalla Fase 1.
- **Fase A — Rifiniture su sezioni già migrate** (~25 pagine, sforzo basso): pagine orfane
  collegate a contenuto già portato — dettagli di `eventi/`, i popup JS di `santomas/`
  lasciati come testo semplice, pagine "nuova cavità" mancanti in `attivi/`.
- **Fase B — Pagine storiche di primo livello** (~25 pagine, valore alto): la cronistoria
  completa del gruppo (`crono.htm`), la serie anniversario/falò mancante agli estremi di
  quella già fatta, racconti di viaggio isolati, bio/memoriali di soci scomparsi
  (verificati uno per uno per non sovrapporsi a pagine reali già migrate da WordPress,
  es. `/museo/chi-era-franco-anelli/`), i corsi 1–4 storici. **Esclusi esplicitamente**
  `cd.htm` e `Statuto.htm`: versioni superate del Consiglio Direttivo e dello statuto, mai
  presentate come equivalenti alle pagine reali di `chi-siamo/` — la stessa regola cardine
  della sezione 1 applicata di nuovo qui.
- **Fase D — Rassegna stampa** (190 pagine): archivio di rassegna stampa 1972–2013, portato
  per intero collegando ogni voce direttamente alla propria scansione, sullo stesso
  modello già in uso per Fax/Gazzetta della pagina Cuba.
- **Fase G — Sezioni tematiche autonome** (~70 pagine, in 4 batch): Trekking, Didattica
  nelle scuole, pannelli della Giornata Nazionale della Speleologia, materiale del III
  Convegno di Speleologia Pugliese, la campagna ambientale sugli ulivi secolari, storia,
  soci, interviste (di cui è emerso che restava solo un'intervista audio come contenuto
  reale, il resto erano pagine frameset/indice duplicate).
- **Fase E — Gallerie fotografiche complete dei corsi** (105 pagine sorgente, riunite in
  16 pagine finali): le gallerie integrali di ogni edizione del corso (23ª–36ª, ~2000 foto
  totali) raccolte ciascuna in un'unica pagina `archivio-fotografico.md` per edizione, più
  i programmi di corso per le edizioni 23ª–25ª.
- **Fase F — Testo integrale degli articoli dei bollettini** (73 pagine sorgente, 72
  migrate): il testo completo dei singoli articoli dei bollettini (1986, 1991, 1996, 1999,
  2001, 2003), con ogni titolo negli indici `bollettino-<anno>.md` ricollegato alla pagina
  reale invece di restare testo semplice non linkato. Incluse, per scelta esplicita
  dell'utente, le due pagine con l'elenco soci.

Ogni fase è stata verificata con lo stesso rito end-to-end: `hugo --gc --minify` (0
errori, conteggio pagine cresciuto del numero atteso), grep mirato per confermare che i
link della fase precedente non puntassero più a testo semplice non collegato, controllo a
vista via screenshot headless-Chrome di un campione di pagine, e **commit separati per
fase** (mai un commit enorme che raccogliesse tutto insieme).

Il generatore applica euristiche e protezioni comuni a tutte le fasi:

- `mode="auto"` in `extract_content()`: estrae sia dal blocco `class="testo"` sia dal
  `<td>` più piccolo con testo ≥90% del massimo, perché la classificazione statica per
  sola presenza di `class="testo"` produceva pagine quasi vuote in diversi template.
- Pulizia automatica di artefatti del vecchio sito: icone stampa/chiudi a fine pagina,
  riferimenti a immagini mai caricate dentro commenti HTML, ancore popup JavaScript.
- Un meccanismo di patch esplicite (`SOURCE_PATCHES`/`POST_FIXUPS`/`TITLE_OVERRIDES`) è
  l'unico ammesso per correggere errori genuini nel sorgente originale (refusi, numerazioni
  incoerenti) — mai per inventare contenuto mancante; ogni patch si arresta con errore se
  il testo atteso non è più presente, così una modifica futura del sorgente non passa
  silenziosamente.
- Una data convenzionale costante su ogni pagina storica priva di data certa, concordata
  con l'utente per evitare che i template Hugo rendessero la data zero-value come
  `01.01.0001`.

**Cosa resta escluso, per scelta esplicita e non per dimenticanza**: le 151 pagine in
inglese (`*_eng.htm`, fuori dalla convenzione "tutto in italiano"), le cartelle `sponsor/`
(stessa decisione presa per il CPT `banner` di WordPress), le revisioni superate
(`*OLD*`/`*NS.htm`), i formati non più riproducibili (`.swf`/`.class`/`.wmv`), e sempre
`Statuto.htm`/`cd.htm` dell'archivio storico.

Al termine delle sette fasi, `PIANO-ARCHIVIO-STORICO.md` è stato aggiornato per
riflettere lo stato "tutte completate", restando come riferimento delle decisioni prese
fase per fase.

## 5. Protezione delle modifiche manuali

Con due script idempotenti che rigenerano `content/` da zero ad ogni rilancio, è emerso un
rischio concreto: perdere correzioni fatte a mano direttamente su un file già generato
(tipicamente per sistemare un layout che pandoc rende male). È stato quindi introdotto
`safe_write_text()`, condiviso da entrambi gli script: prima di sovrascrivere un file,
confronta l'hash del contenuto attuale su disco con l'hash dell'ultimo contenuto scritto
dallo script stesso (tenuto in `.content-manifest.json`). Se il file è stato modificato a
mano nel frattempo, lo script **non lo sovrascrive**: salva una copia in
`manual-backups/`, stampa un avviso e lo riepiloga a fine esecuzione. Solo un rilancio
esplicito con `--force` disattiva la protezione — e per convenzione del progetto, non va
mai usato senza conferma esplicita dell'utente.

## 6. Consolidamento: tassonomie, layout, correzioni di bug

Con la maggior parte del contenuto reale in sede, il lavoro si è spostato su rifiniture
strutturali:

- **Tassonomie**: oltre a `category` (già usata da `categories:` nei post di `novita/`),
  aggiunta la tassonomia `anno` → `anni`, per rendere il widget "Archivi" della sidebar un
  elenco di link reali per anno invece di semplice testo. Nota tecnica non ovvia: il
  campo nel front matter deve usare il valore **plurale** della configurazione (`anni:`),
  non la chiave singolare (`anno:`) — quest'ultima compila senza errori ma non genera
  nessuna pagina, silenziosamente.
- **Backfill delle date reali** su tutto l'archivio storico e sui bollettini, con fix del
  bug di rendering della data zero-value.
- **Paginazione uniforme**: `layouts/_default/list.html` ha iniziato a paginare ogni
  sezione con `.Paginate` esattamente come la home — prima solo la home paginava, e
  sezioni lunghe (es. `archivio-storico/eventi`, 69 pagine) venivano renderizzate tutte
  su una pagina sola.
- **Due bug di layout CSS risolti**, non evidenti dal solo codice:
  1. Il menu compariva spostato a destra invece che come barra orizzontale sotto
     l'header, perché `.site-header` era un unico contenitore flex con due figli senza
     una larghezza esplicita sul secondo. Risolto separando il titolo in un blocco
     dedicato (`.site-header__hero`) e lasciando la `.navbar` a piena larghezza subito
     sotto.
  2. Tutti i sottomenu restavano sempre aperti, non solo al passaggio del mouse: la
     regola `.nav-main ul { display: flex; }` (senza il combinatore diretto `>`) si
     applicava per errore anche ai sottomenu discendenti, vincendo per specificità su
     `display: none`. Risolto restringendo la regola a `.nav-main > ul`. Bug di
     specificità CSS individuato solo grazie a screenshot reali, non da una lettura del
     CSS che "sembrava a posto".
- **Correzioni di deformazione delle immagini** nelle griglie a schermi stretti, e
  ingrandimento delle foto nelle gallerie dell'archivio storico (da una a due colonne).
- **Pagina di licenza** aggiunta (CC BY-NC-SA 4.0) con link in sidebar.
- **Header con logo**: aggiunto il logo ufficiale prima del titolo "Gruppo Puglia Grotte",
  prima impilato sopra il titolo, poi — su richiesta dell'utente — riposizionato in linea
  col titolo stesso, con il sottotitolo riallineato orizzontalmente alla "G" di "Gruppo".
  La soluzione finale usa un layout CSS Grid (`grid-template-columns: auto 1fr`, logo con
  `grid-row: 1 / span 2`) dopo che un primo tentativo in flexbox si è rivelato instabile:
  `flex-wrap: wrap` valuta se andare a capo usando la dimensione max-content (non
  wrappata) degli elementi, quindi con un titolo largo il logo veniva spinto su una riga
  propria invece di lasciare che fosse solo il testo del titolo a wrappare — bug scoperto
  e corretto durante la verifica con screenshot, prima di essere segnalato dall'utente.
- **Bug del "mezzo header" su iPhone Safari**, segnalato dall'utente via screenshot
  WhatsApp: diagnosticato come `background-size: cover` combinato con `min-height: 0` su
  mobile, che permetteva al box dell'header di crescere oltre l'altezza nativa
  dell'immagine di sfondo (230px), forzando uno zoom eccessivo con crop a una sottile
  striscia sfocata. Prima di intervenire, è stato escluso che si trattasse di un problema
  di cache confrontando l'HTML/CSS live in produzione con l'HEAD corrente di git (identici).
  Risolto fissando `background-size: auto 230px` + `background-repeat: no-repeat` (la
  seconda proprietà necessaria per evitare che l'immagine, non più a `cover`, venisse
  ripetuta a mosaico in un box più alto del previsto).
- **Rinomina nel footer**: la quarta colonna del footer è diventata "Social media"; la
  voce "Ambiente" nel footer è stata sostituita con "Archivio storico", per coerenza con
  il menu principale (la pagina `/ambiente/` resta comunque pubblicata e raggiungibile via
  URL diretto, solo non più in navigazione).

## 7. Nuovi contenuti aggiunti direttamente in Hugo

Oltre alla migrazione, sono stati creati contenuti nuovi, mai esistiti su WordPress:

- La pagina del volume "Castellana e le sue grotte" (2021).
- L'annuncio del 52° corso di introduzione alla speleologia, con relativa pagina di
  dettaglio.
- Dettagli del Museo, di Monopoli e delle uscite 2006–2007 (11 pagine).
- **La sezione "Relazioni Uscite"**: tre relazioni di uscita speleologica scritte dai soci
  (Grave Rotolo, Grotta del Ciolo, Grotta del Mezzogiorno e Frasassi), trasformate da PDF
  sorgente in pagine Markdown complete di immagini — estratte dai PDF originali via
  `pdfimages -j` quando incorporate come JPEG nativi, o via rasterizzazione dell'intera
  pagina con `pdftoppm` seguita da ritaglio con PIL quando l'immagine aveva un layer di
  trasparenza (smask) non composito automaticamente. La sezione è stata collegata al menu
  principale (voce "Relazioni Uscite", tra Corsi e Pubblicazioni), al footer, e — in due
  correzioni successive segnalate dall'utente — completata con la categoria tassonomica
  "Relazioni" e con il campo `anni:` corretto per ciascuna relazione, necessario perché le
  pagine comparissero nel widget "Archivi" della sidebar.

## 8. Verifica continua

In tutto il progetto, ogni modifica è stata verificata con lo stesso protocollo:
`hugo --gc --minify` per un build pulito (0 errori, conteggio pagine tracciato prima e
dopo), un server HTTP locale temporaneo per controllare via `curl` che ogni URL nuovo o
modificato rispondesse 200, screenshot con Chrome headless per il controllo visivo
(incluso, nei casi più delicati, un campionamento dei pixel via PIL/numpy per distinguere
un artefatto di rendering sottile — come una fascia di colore piatto al posto di una
texture fotografica — da un problema reale), e commit separati per ambito di modifica con
messaggi descrittivi in italiano.

## 9. Stato attuale e prossimi passi

Il sito genera oggi centinaia di pagine con 0 errori, tutto il contenuto reale (pagine
WordPress, post, e l'intero archivio storico pre-WordPress recuperato in sette fasi), un
menu e una sidebar fedeli ai dati reali del vecchio sito, e diversi contenuti nuovi
aggiunti direttamente in Hugo. I prossimi passi consigliati, descritti in dettaglio in
`README.md`, restano:

1. Migrare gli allegati WordPress ancora non referenziati da nessun contenuto reale
   (~130MB non copiati perché non citati in nessuna pagina/post pubblicato).
2. Un'eventuale Fase 3 su cartelle dell'archivio storico non ancora scoping-ate, solo su
   richiesta esplicita.
3. Configurare i redirect 301 lato server in produzione (oltre agli `aliases:` già
   generati) per il pieno beneficio SEO.
4. Valutare un offuscamento via JavaScript degli indirizzi email in pagina, se serve
   ridurre l'esposizione agli scraper rispetto al semplice `mailto:`.
