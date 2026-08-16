# Migrazione gruppopugliagrotte.it → Hugo

## Come è stato costruito

Una prima versione di questo scaffold (fatta senza accesso al sito live, bloccato da
`robots.txt`, né al database) usava menu, sidebar e colore dell'header **indovinati** da
snippet di ricerca, lasciando esplicitamente vuote (con un commento
`<!-- TODO migrazione -->`) le pagine dove non era possibile recuperare fatti reali
(nominativi del Consiglio Direttivo, testo dello statuto).

Questa versione sostituisce quasi tutto quel materiale indovinato con dati reali, a
partire da una copia completa dell'installazione WordPress (`../home/`, incluso
`wp-content/uploads/`) e da un dump SQL (formato UpdraftPlus). Il dump è stato importato
in un container MariaDB locale e interrogato direttamente (niente parsing di WXR o
PHP-serialize a mano); lo script `scripts/wp_to_hugo.py` genera tutto `content/` da lì.
Vedi `CLAUDE.md` per i dettagli della ricognizione e le decisioni prese.

## Palette e tipografia (dal file originale del tema)

Estratte dal vero `style.css` di **Twenty Thirteen** (v4.2, tema standard
WordPress.org), fornito dall'utente e conservato in
`riferimento/twentythirteen-style.css`.

| Token | Valore | Uso nel tema originale |
|---|---|---|
| `--color-bg` | `#FFFFFF` | `.site` |
| `--color-cream` | `#F7F5E7` | `.navbar`, `.widget`, `.no-comments` |
| `--color-cream-deep` | `#E8E5CE` | `.site-footer` |
| `--color-maroon-900` | `#220E10` | hover/voce attiva del menu, fascia widget del footer |
| `--color-ink` | `#141412` | testo del corpo |
| `--color-link` | `#CA3C08` | link |
| `--color-link-visited` | `#AC0404` | link visitato |
| `--color-link-hover` | `#EA9629` | link al passaggio del mouse |
| `--color-accent` | `#BC360A` | meta dei post, voce di menu corrente |
| `--color-submenu-hover` | `#DB572F` | sottomenu al passaggio del mouse |
| `--color-footer-link` | `#E6402A` | link nei widget del footer |

Font: **Bitter** (titoli) e **Source Sans Pro** (corpo del testo; su Google Fonts oggi
distribuito come "Source Sans 3", stessa famiglia). Nessun font monospazio.

Misure di impaginazione dal file originale: `.site` largo fino a 1600px, header/nav
contenuti in 1080px, colonna articolo 604px (senza sidebar) o 1040px con sidebar 300px —
token `--site-max`, `--header-max`, `--content-max`, `--measure`, `--sidebar-w`.

## Cosa era indovinato ed è ora confermato dal DB reale

| Elemento | Prima | Ora (fonte: dump SQL, container `gpg-mysql-tmp`) |
|---|---|---|
| Colore testo header | bianco (ipotesi) | `#f4f3bc`, da `theme_mods_twentythirteen` |
| CSS aggiuntivo/child theme | non verificato | nessuno: `wp_posts` non ha righe `post_type='custom_css'`, nessun plugin di CSS custom installato |
| Menu di navigazione | ricostruito da snippet | ricostruito da `wp_posts`/`wp_postmeta` (`nav_menu_item`), inclusa la sezione **Ambiente** mancante prima |
| Sidebar | box "Scheda"/"Link rapidi"/"Social" inventati | widget reali: Articoli recenti, Archivi (per anno), Categorie, testo "Copyright" (dati legali reali dell'associazione) — Archivi e Categorie sono link veri, non testo (vedi "Tassonomie" più sotto) |
| Genericons | dichiarato in `style.css`, font assente | copiato da `wp-content/themes/twentythirteen/genericons/`, usato per l'icona data nei post e per le icone social nel footer |
| Statuto / Consiglio Direttivo | placeholder esplicito, mai inventato | testo integrale reale dal DB |

Il file originale del tema resta in `riferimento/twentythirteen-style.css` per confronto.

## Immagine di intestazione

`cropped-sfondo1.jpg` (1600×230px), copiata in `static/images/header/sfondo1.jpg` e
applicata come sfondo di `.site-header__hero`. Confermata reale anche via DB
(`theme_mods_twentythirteen.header_image`, stesso file).

Il titolo e la tagline sono centrati verticalmente in quel blocco (`align-items: center`
su `.site-header__hero`), coerente col tema originale (lì `.site-title` ha
`padding-top: 58px` su un box di 230px, non un allineamento in basso).

## Header e menu: due bug di layout risolti

Non evidenti dal solo codice — utile saperli se si ritocca `static/css/style.css`:

1. **Menu spostato a destra invece di barra orizzontale sotto l'header.**
   `.site-header` era un unico contenitore flex con due figli (il blocco titolo e la
   `.navbar`): senza una larghezza esplicita sul secondo, i due finivano affiancati in
   riga invece che impilati. Risolto separando il titolo in un blocco dedicato,
   `.site-header__hero` (immagine, altezza, centratura), lasciando `.navbar` come
   elemento normale a piena larghezza subito sotto.
2. **Tutti i sottomenu sempre aperti, non solo al passaggio del mouse.** La regola
   `.nav-main ul { display: flex; ... }` (senza il combinatore diretto `>`) si applicava
   per errore anche a `.sub-menu` (un `<ul>` discendente), e vinceva per specificità su
   `.sub-menu { display: none; }`. Risolto scrivendo `.nav-main > ul` per limitare
   `display: flex` al solo elenco di primo livello.

Verificato con screenshot reali (headless Chrome), non solo leggendo il CSS: un
"sembra a posto" visivo può nascondere bug di specificità come il secondo.

## Footer: icone social

`layouts/partials/footer.html` usa i Genericons reali (stessi file del tema, vedi sopra)
per Facebook, X/Twitter, YouTube e Instagram — icone monocromatiche (ereditano il colore
testo del footer, non loghi colorati), niente bordo perché sono glifi di un font, non
immagini. URL in `hugo.toml` → `[params]`: i primi tre erano già presenti, Instagram è
stato aggiunto da un URL reale trovato in `content/chi-siamo/contatti.md` (non è nel DB
come widget/theme_mod, quindi non c'è una query SQL "fonte" per questo).

## Tassonomie: Archivi e Categorie

`hugo.toml` dichiara `[taxonomies]` con `category` (default Hugo, già usato dal campo
`categories:` nei post di `novita/`) e una tassonomia aggiuntiva `anno` → `anni`, per
generare pagine di archivio reali per anno (`/anni/2019/`, ecc.) invece di semplice testo
nella sidebar. Genera anche `/categories/<slug>/`.

Nota per chi tocca `scripts/wp_to_hugo.py` o `hugo.toml`: **il nome del campo nel front
matter deve essere il valore plurale della config, non la chiave singolare** — con
`anno = "anni"` il campo va scritto `anni: "2019"`, non `anno: "2019"` (questo secondo
tentativo compila senza errori ma non genera nessuna pagina, silenziosamente). La stessa
convenzione vale per `category = "categories"`, dove infatti il campo si chiama già
`categories:`.

## Archivio storico (sito pre-WordPress, 1999–2014)

Oltre al contenuto WordPress, il sito ha avuto una vita precedente come sito statico
fatto a mano (Dreamweaver, layout a tabelle, codifica ISO-8859-1): una copia completa
(`../old/www.gruppopugliagrotte.it/`, 949 pagine `.htm`, 736MB) è stata fornita
dall'utente. Alcune di quelle pagine erano ancora linkate — con URL assoluti oggi rotti —
da contenuto reale già migrato (es. `storiagpg.htm`, `museo.htm`, i PDF sotto
`esplorazioni/alburni/`). La migrazione di questo materiale è avvenuta in due fasi, con lo
script separato `scripts/old_to_hugo.py` (stdlib Python + `pandoc`, stesso vincolo "niente
pip" di `wp_to_hugo.py`), che scrive **solo** sotto `content/archivio-storico/` e non tocca
mai `content/` WordPress (`PAGES`/`write_index()` restano una pipeline a parte da
`EVENTI_FILES`/`CORSI_FILES`/`extend_archive()`):

- **Fase 1** (`python3 scripts/old_to_hugo.py`, funzione `main()`): le 16 pagine/asset
  citati da link reali già migrati — convertite in Markdown vero, con i link nel contenuto
  WordPress riscritti dagli URL assoluti rotti ai nuovi permalink relativi. 17 file in
  `content/archivio-storico/` (16 pagine + `_index.md` della sezione).
- **Fase 2** (`python3 scripts/old_to_hugo.py --extend`, funzione `extend_archive()`):
  cronaca eventi 2003–2014 (69 pagine, `content/archivio-storico/eventi/`) e le edizioni
  18–36 del corso di speleologia (19 pagine, `content/archivio-storico/corsi/`) — materiale
  storico reale mai duplicato altrove, organizzato come sottosezioni dedicate su richiesta
  esplicita dell'utente, senza toccare nessun contenuto già migrato (verificato ad ogni
  rigenerazione confrontando l'md5 di `content/chi-siamo/consiglio-direttivo.md`, che
  l'utente modifica a mano in parallelo).

Asset copiati solo se effettivamente referenziati (792 file, ~79MB) in
`static/archivio-storico/legacy/`, non l'intera cartella `old/`.

**Cosa resta escluso, e perché** (decisioni prese, non dimenticanze):

| Escluso | Motivo |
|---|---|
| `*_eng.htm` (151 file) | contenuto in inglese, fuori dalla convenzione "tutto in italiano" |
| `rass_ita.htm` + `rassegna/` | indice di ~180 ritagli stampa scannerizzati, fuori scope — eventuale archivio a sé in futuro |
| `sponsor/` | cruft pubblicitario, stessa decisione già presa per il CPT WordPress `banner` |
| `*OLD*`/`*NS.htm` | revisioni superate, tenuta solo la versione più recente per ogni pagina |
| `.swf`/`.class`/`.wmv` | formati non riproducibili sul web moderno |
| `Statuto.htm`/`cd.htm` di `old/` | versioni **superate** di Statuto e Consiglio Direttivo — mai da unire o linkare come equivalenti alle pagine correnti di `chi-siamo/`, per la regola cardine "non confondere contenuto istituzionale" |
| `bollettini/`, `didattica/`, `Trek/`, `santomas/` (oltre l'index), `GNS/`, `attivi/` (oltre `programma0607.htm`), `esplorazioni/` (oltre i PDF già presi), `convreg/` (oltre `programma.htm`), `interviste/`, `ulivi/` | non ancora scoping-ati: candidati per un'eventuale Fase 3, non ancora richiesta |

**Vincoli tecnici applicati nel generatore** (utili se lo si riestende):

- `mode="auto"` in `extract_content()`: estrae sia dal blocco `class="testo"` sia dal
  `<td>` più piccolo con testo ≥90% del massimo, tiene il risultato più lungo — necessario
  perché la classificazione statica per sola presenza di `class="testo"` produceva pagine
  quasi vuote su diverse pagine (es. `corso25.htm`–`corso36.htm`, dove il template ha un
  unico `<td>` esterno che avvolge sia il menu di navigazione sia il contenuto reale).
- `strip_print_close_widget()`, `strip_html_comments()`, `strip_popup_anchors()`: puliscono
  automaticamente gli artefatti del vecchio sito (icone stampa/chiudi a fine pagina,
  riferimenti a immagini mai caricate dentro commenti HTML, ancore popup JavaScript).
- `SOURCE_PATCHES` / `POST_FIXUPS` / `TITLE_OVERRIDES`: unico meccanismo ammesso per
  correggere errori genuini nel sorgente originale (HTML malformato, refusi come "Il
  XIIIV Corso" → "Il XVIII Corso", numerazione decimale incoerente "23°" → "XXIII") — mai
  per inventare contenuto mancante; ogni patch fa `sys.exit` se il testo atteso non è più
  presente, così una modifica futura del sorgente non passa silenziosamente.
- `date: 2026-08-01` (costante `DATE_RIMIGRAZIONE`) su ogni pagina storica priva di data
  certa nel sorgente: convenzione concordata con l'utente per evitare il bug dei template
  Hugo che formattano la data zero-value (`0001-01-01`) come `01.01.0001` quando manca il
  campo `date:`.

## Cosa non è stato riportato (di proposito)

Il sito WordPress espone diversi elementi privi di senso su un sito statico Hugo,
volutamente omessi: link `wp-admin`/login autore, pagine archivio autore, il prompt
nativo dei commenti WP, un banner sponsor storico isolato (post_type `banner`, un solo
elemento). Il widget "Cerca" della sidebar reale è omesso per lo stesso motivo — niente
casella di ricerca finta senza un motore vero (es. Pagefind) dietro.

Se in futuro servono i commenti, un'opzione statica comune è Giscus o Utterances.

## Struttura del contenuto

```
content/
├── _index.md                          → home (layouts/index.html, elenco da novita/)
├── novita/{_index,29 post}            → i post reali del blog WP, con categorie e anno (anni:)
├── eventi/{_index,4 pagine evento}    → pagina evento "evergreen" del menu (diversa da novita/)
├── chi-siamo/{_index,contatti,consiglio-direttivo,statuto}
├── esplorazioni/{_index,nazionali/,internazionali/,cavita-artificiali}
├── corsi/{_index,10 edizioni}         → edizioni recenti (37ª in poi), dato WordPress reale
├── pubblicazioni/{_index,convegni,bollettini-puglia-grotte/}
├── museo/{_index,chi-era-franco-anelli}
├── ambiente/_index.md                 → contenuto assente anche a monte (vedi sotto)
└── archivio-storico/                  → sito pre-WordPress (1999–2014), vedi sezione dedicata sopra
    ├── _index.md + 16 pagine Fase 1
    ├── eventi/{_index,69 pagine}      → cronaca 2003–2014
    └── corsi/{_index,19 pagine}       → edizioni 18ª–36ª
```

180 file Markdown in totale (42 pagine + 29 post WordPress + 104 pagine/indici
dell'archivio storico + gli `_index.md` di sezione).

Due pagine WordPress restano `<!-- TODO migrazione -->` non per un limite della
migrazione ma perché **il DB conferma che sono vuote anche sul sito originale**:
`ambiente/_index.md` e `esplorazioni/cavita-artificiali.md`. Non vanno riempite con
testo plausibile.

## Link interni

Tutti i link assoluti al vecchio dominio (`gruppopugliagrotte.it/home/...`) nel contenuto
reale sono riscritti da `scripts/wp_to_hugo.py` verso il percorso Hugo corrispondente,
non lasciati come redirect via alias: pagine/post reali, allegati sotto
`wp-content/uploads/`, file nella cartella legacy `home/downloads/` (moduli di iscrizione,
locandine — copiati in `static/downloads/`), e le "pagine-allegato" che WordPress genera
per mostrare un file caricato (risolte per slug fino al file reale).

Il contenuto reale, però, cita spesso anche link assoluti FUORI da `/home/`: puntano alla
radice del sito pre-WordPress (es. `storiagpg.htm`, `images/anelli.jpg`,
`esplorazioni/alburni/*.pdf`), quello coperto da `scripts/old_to_hugo.py` (vedi "Archivio
storico" più sopra). Ogni volta che quello script gira (una qualunque delle tre fasi) scrive
la sua mappa completa `LINK_REWRITE` in `.link-rewrite.json` alla radice del repo (fondendo,
non sovrascrivendo, con quanto già presente — le tre fasi si possono rilanciare
indipendentemente). `scripts/wp_to_hugo.py` legge quel file e riscrive questi link assoluti
verso il permalink Hugo o l'asset statico corrispondente, esattamente come fa per `/home/`.
**Per questo l'ordine di esecuzione conta**: va rilanciato prima `old_to_hugo.py` (tutte le
fasi che servono) e poi `wp_to_hugo.py`, altrimenti quest'ultimo trova `.link-rewrite.json`
incompleto o assente e lascia il link assoluto invariato, segnalandolo in `== Avvisi ==`
invece di romperlo in silenzio.

Restano volutamente non toccati solo i link a un sito ancora più vecchio, pre-1999, di cui
non esiste alcuna copia da migrare (già rotti anche sul sito originale).

## Script di conversione

`scripts/wp_to_hugo.py` (stdlib Python + `pandoc` in PATH, nessuna dipendenza pip):
legge pagine/post/categorie/allegati dal DB via `docker exec gpg-mysql-tmp mysql`,
converte l'HTML in Markdown con pandoc, gestisce gli shortcode `[gallery]`/`[caption]`/
`[embed]`, riscrive i link alle immagini e copia solo gli allegati effettivamente
referenziati in `static/images/uploads/`. È idempotente: si può rilanciare dopo aver
corretto la mappa pagina→percorso (`PAGE_MAP` in cima al file) senza effetti collaterali.

```sh
python3 scripts/wp_to_hugo.py
```

Richiede il container MariaDB locale con il DB già importato:

```sh
docker run -d --name gpg-mysql-tmp -e MYSQL_ROOT_PASSWORD=temppass \
  -e MYSQL_DATABASE=gpg -p 127.0.0.1:33061:3306 docker.io/library/mariadb:10.11
docker exec -i gpg-mysql-tmp mysql -uroot -ptemppass gpg < ../backup_*-db
```

Per l'archivio storico (Fase 1 + Fase 2, sito pre-WordPress) c'è uno script separato,
`scripts/old_to_hugo.py`, che non richiede il container MariaDB (nessun DB: sono file
statici) — legge direttamente da `../old/www.gruppopugliagrotte.it/`:

```sh
python3 scripts/old_to_hugo.py               # Fase 1: le 16 pagine linkate da contenuto reale
python3 scripts/old_to_hugo.py --extend       # Fase 2: cronaca eventi 2003–2014 + corsi 18ª–36ª
python3 scripts/old_to_hugo.py --bollettini   # Fase 3: indici dei bollettini 1984–2008
```

Idempotente come `wp_to_hugo.py`: si può rilanciare in sicurezza, non tocca mai
`content/` WordPress. Dettagli su euristiche di estrazione e limiti nella sezione
"Archivio storico" più sopra.

### Protezione delle modifiche manuali

Entrambi gli script sono idempotenti per design (un rilancio rigenera tutto da zero),
il che è in conflitto con eventuali correzioni fatte a mano su un file già generato
(es. sistemare un layout che pandoc rende male). Per questo motivo, prima di sovrascrivere
un file che esiste già, ogni scrittura passa da `safe_write_text()`, che confronta l'hash
del contenuto attuale su disco con l'hash dell'ULTIMO contenuto scritto dallo script
stesso (tenuto in `.content-manifest.json`, alla radice del repo, condiviso dai due
script):

- se il file su disco corrisponde ancora a quanto scritto l'ultima volta dallo script,
  viene sovrascritto normalmente;
- se invece è stato modificato a mano nel frattempo, lo script **non lo sovrascrive**:
  salva una copia della versione attuale (quella modificata a mano) in
  `manual-backups/<stesso percorso relativo a content/>`, stampa un avviso
  `SALTATO (modificato a mano dopo l'ultima generazione): ...` e lo riepiloga a fine
  esecuzione sotto `== File con modifiche manuali non sovrascritti ==`.

Per rigenerare comunque un file protetto (accettando di perdere la modifica manuale,
dopo averla eventualmente confrontata con la copia in `manual-backups/`), rilancia lo
script con `--force`, che disattiva il controllo per l'intera esecuzione.

`.content-manifest.json` e `manual-backups/` sono fuori da `content/`: Hugo non li
processa mai come pagine.

## Layout e template

```
layouts/
├── _default/{baseof,single,list}.html   → list.html paginato (paginate = 8 in hugo.toml),
│                                            stesso pattern di index.html/home
├── index.html                 → home: elenco notizie da novita/ (paginato) + sidebar
└── partials/
    ├── head.html
    ├── header.html            → .site-header__hero (immagine+titolo) + .navbar separati
    ├── footer.html            → colonne footer + icone social (Genericons)
    ├── sidebar-scheda.html    → widget reali, Archivi/Categorie come link (vedi sopra)
    └── post-list-item.html
```

Il menu è definito in `hugo.toml` sotto `[[menu.main]]`, ricostruito dal menu reale di
WordPress (vedi `CLAUDE.md`). L'ultima voce, "Ambiente" nella prima versione, punta ora a
`/archivio-storico/` (la pagina `/ambiente/` resta pubblicata e raggiungibile via URL
diretto, solo non più in navigazione, su richiesta esplicita dell'utente).

`layouts/_default/list.html` pagina ogni sezione con `.Paginate` esattamente come la
home — prima solo la home paginava, e sezioni lunghe (es. `archivio-storico/eventi`, 69
pagine) venivano renderizzate tutte su una sola pagina senza controlli di navigazione a
fondo pagina.

## Foglio di stile

Un unico file, `static/css/style.css`, con i token di design come custom property CSS in
`:root`. Nessun preprocessore richiesto.

## Provare in locale

```sh
hugo server -D -F       # http://localhost:1313/, con bozze e contenuto futuro
hugo --gc --minify      # build di produzione
```

oppure, tramite il `Makefile` (vedi sezione dedicata sotto):

```sh
make serve    # equivalente a "hugo server -D -F"
make build    # equivalente a "hugo --gc --minify"
```

Validato: 241 pagine generate (180 dal contenuto reale + sezioni/tassonomie/paginazione
automatiche), 0 errori, 105 alias funzionanti verso i vecchi URL — sia WordPress
(`/home/...`) sia, dove aveva senso, il sito pre-WordPress.

## Makefile: build, bozze/contenuto futuro, pulizia, pubblicazione FTP

Per facilitare il build, preview e delivery delle pagine generate si usa il programma `make` che deve essere installato insieme a `hugo`
per la gestione del contenuto. Oltre a questo, per la pubblicazione delle pagine su Aruba occorre il programma `lftp`.

In particolare su Debina/Ubuntu

```
sudo apt install -y make hugo lftp
```

Il `Makefile` distribuito copre l'intero ciclo locale e la pubblicazione, pensato per l'hosting Aruba
(FTP). Target principali (`make help` li elenca tutti):

| Target | Effetto |
|---|---|
| `make build` | build di produzione (`hugo --gc --minify`) |
| `make build-drafts` / `build-future` / `build-all` | come sopra, con `-D`/`-F`/entrambi — utile per vedere anche pagine `draft: true` o datate nel futuro (es. `di-nuovo-il-nuovo-sito.md`, 2026-08-15) |
| `make serve` / `serve-prod` | server locale, con o senza bozze/contenuto futuro |
| `make clean` | rimuove `public/`, `resources/`, `.hugo_build.lock` |
| `make publish-dry-run` | build + `lftp mirror --reverse --delete --dry-run`: mostra cosa cambierebbe sul server senza caricare nulla |
| `make publish` | build + upload reale via `lftp` (mirror completo: carica i file nuovi/modificati e **cancella** sul server quelli non più presenti in `public/`) |

Le credenziali FTP non vanno mai scritte nel `Makefile`: vanno in un file locale
`.env.ftp` (mai committato), a partire dal template `.env.ftp.example`:

```sh
cp .env.ftp.example .env.ftp   # poi compilare FTP_HOST/FTP_USER/FTP_PASS
make publish-dry-run           # verifica prima di toccare il sito live
make publish
```

Richiede `lftp` installato (`sudo apt-get install -y lftp` su Debian/Ubuntu);
`check-ftp-vars` fallisce con un messaggio esplicito se manca `.env.ftp` o `lftp`.
Supporta sia `ftp://` sia `ftps://` (variabile `FTP_PROTOCOL`), modalità passiva attiva
di default (comune dietro NAT/firewall sull'hosting condiviso).

## Prossimi passi consigliati

Verificato lo stato reale di ogni punto (non solo l'intenzione originale) l'ultima volta
il 16/08/2026: 1 e 2 sono ancora aperti, nessuno dei quattro è completo.

1. **Migrare gli allegati WordPress non referenziati.** Ancora non iniziato: su 604 file
   in `wp-content/uploads/` originale, solo 122 sono stati copiati in
   `static/images/uploads/` (quelli citati da contenuto reale già migrato) — restano 482
   file (~130MB) mai copiati né linkati da nessuna parte. Prima di migrarli in blocco
   andrebbe deciso *dove* dovrebbero comparire (nessuna pagina li cita, quindi non basta
   copiarli: serve capire a quale contenuto appartenevano in origine, o accettare che
   restino un archivio scaricabile senza una pagina che li introduce).
2. **Fase 3 dell'archivio storico**, parzialmente avanzata rispetto a quando questo punto
   fu scritto — non più "da valutare se iniziare", ma da completare:
   - **Fatto**: `didattica/`, `Trek/` (→ `content/archivio-storico/trekking-di-primavera/`),
     `santomas/` (→ `progetto-santo-tomas/`), `GNS/` (→ `gns/`), `ulivi/` — tutte con
     contenuto reale, non solo pagine indice.
   - **Parziale**: `bollettini/` — gli indici 1984–2008 esistono (`content/pubblicazioni/
     bollettini-puglia-grotte/`), ma la conversione integrale dei singoli articoli copre
     solo 6 annate (`content/archivio-storico/bollettini/{1986,1991,1996,1999,2001,2003}/`)
     sulle ~34 pagine `.htm` sorgente in `old/bollettini/`.
   - **Non iniziate**: `esplorazioni/` (pagine di singola uscita ancora fuori:
     `pietro.htm`, `luca.htm`, `iazzo.htm`, `chiancone.htm`/`chiancone1.htm`/
     `chiancone2.htm`, `mamutte.htm`, `gentili.htm`, `sammichele.htm`, `impalata.htm`,
     `Polignano.htm`, `portagrande.htm`, `progettocatasto.htm` — oltre a `monopoli*.htm`
     e `alburni/`, già fatti); `convreg/` (`spelaion.htm`, `mostra.htm`, `Sponsor/` — oltre
     a `programma.htm`/`risultati.htm`/`immagini.htm`, già fatti a mano su
     `iii-convegno-speleologia-pugliese/`); `attivi/` (7 pagine di uscita ancora fuori:
     `braca.htm`, `laterza.htm`, `notarvincenzo.htm`, `calzino.htm`, `pila.htm`,
     `angelo.htm`, `preveticelli.htm` — oltre a `volpe.htm`/`pulo.htm`, già fatti);
     `interviste/` — mai affrontata, ma quasi tutto il materiale è audio/video non
     testuale (`CNR19.07.08.wmv`/`.mp3`/`.swf`), probabilmente non ha senso convertirlo in
     Markdown: da valutare se vale la pena solo per le pagine indice.
3. ~~Redirect 301 lato server~~ **Fatto** (16/08/2026): `static/.htaccess`, generato da
   `python3 scripts/generate-htaccess.py` — un upgrade HTTPS (`RewriteRule`, verificato
   che serve davvero: `http://www.gruppopugliagrotte.it/` rispondeva 200 in chiaro,
   Aruba non lo fa automaticamente a monte) + una `RedirectMatch 301` per ognuno di 168
   URL storici reali (72 dagli `aliases:` di WordPress nel front matter di
   `content/**/*.md`, 96 dal `LINK_REWRITE` del sito pre-WordPress in
   `scripts/old_to_hugo.py`) verso i rispettivi nuovi permalink. Passa da `static/` come
   qualunque altro asset, incluso automaticamente in `make publish`. Non sostituisce gli
   `aliases:` di Hugo (restano utili per l'anteprima locale, dove `.htaccess` non ha
   effetto): li rende ridondanti solo in produzione, dove contano i redirect HTTP veri,
   non il `<meta http-equiv="refresh">` più debole che genera Hugo da solo. Rigenerare
   con lo stesso script (non a mano) se cambia un permalink — usa una destinazione
   temporanea via `hugo --config hugo.toml,scripts/htaccess-extra.toml`, non tocca la
   build normale.

   **Incidente in produzione, risolto lo stesso giorno**: una prima versione includeva
   anche 6 redirect dalle vecchie varianti di `index.htm` verso la home. Appena
   caricate, hanno mandato la home in un loop di redirect 301 su se stessa (sito
   irraggiungibile per il tempo della diagnosi) — causa non accertata fino in fondo
   (sospetto: `RedirectMatch` con target uguale alla document root che interagisce male
   con `mod_dir`/`DirectoryIndex` su questo hosting, mai verificato lato server, nessun
   accesso alla config Apache oltre FTP). Isolato per bisezione diretta contro il server
   reale, non riproducibile in locale. Categoria rimossa dal generatore invece di essere
   ritentata: per 6 vecchi nomi di homepage praticamente mai linkati da fuori non vale
   il rischio. Se si vuole reintrodurla in futuro: testarla PRIMA su un URL di prova
   non-root, mai direttamente su `/`.
4. **Email meno esposte agli scraper**, ancora tutte in chiaro: 44 file in `content/`
   contengono un `mailto:` diretto, per almeno 16 indirizzi reali distinti (ruoli
   istituzionali: `presidente@`, `segreteria@`, `webmaster@`, `direttorescuola@`, ecc. —
   `grep -rhoE '[a-zA-Z0-9._%+-]+@(gruppopugliagrotte|grottedicastellana)\.it' content/`
   per l'elenco completo). Tecnica tipica: non scrivere l'indirizzo nell'HTML, ma
   ricostruirlo a runtime via JS da attributi separati (es. `data-user="presidente"
   data-domain="gruppopugliagrotte.it"` sul link, un piccolo script al caricamento della
   pagina compone `mailto:` e lo inietta) — gli scraper che leggono solo l'HTML statico
   non vedono l'indirizzo, un browser reale sì. Da NON fare: cambiare o rimuovere gli
   indirizzi stessi, sono dati istituzionali reali.
