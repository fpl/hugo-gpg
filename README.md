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
├── novita/{_index,28 post}            → i post reali del blog WP, con categorie e anno (anni:)
├── eventi/{_index,4 pagine evento}    → pagina evento "evergreen" del menu (diversa da novita/)
├── chi-siamo/{_index,contatti,consiglio-direttivo,statuto}
├── esplorazioni/{_index,nazionali/,internazionali/,cavita-artificiali}
├── corsi/{_index,10 edizioni}
├── pubblicazioni/{_index,convegni,bollettini-puglia-grotte/}
├── museo/{_index,chi-era-franco-anelli}
└── ambiente/_index.md                 → nuova sezione, contenuto assente anche a monte (vedi sotto)
```

72 file Markdown in totale (42 pagine + 28 post + gli `_index.md` di `novita/` e della home).

Due pagine restano `<!-- TODO migrazione -->` non per un limite della migrazione ma
perché **il DB conferma che sono vuote anche sul sito originale**: `ambiente/_index.md` e
`esplorazioni/cavita-artificiali.md`. Non vanno riempite con testo plausibile.

## Link interni

Tutti i link assoluti al vecchio dominio (`gruppopugliagrotte.it/home/...`) nel contenuto
reale sono riscritti da `scripts/wp_to_hugo.py` verso il percorso Hugo corrispondente,
non lasciati come redirect via alias: pagine/post reali, allegati sotto
`wp-content/uploads/`, file nella cartella legacy `home/downloads/` (moduli di iscrizione,
locandine — copiati in `static/downloads/`), e le "pagine-allegato" che WordPress genera
per mostrare un file caricato (risolte per slug fino al file reale). Fanno eccezione, e
restano non toccati, i link a un sito pre-WordPress ancora più vecchio (pagine `.htm` sotto
un'altra struttura, es. `/convreg/programma.htm`) di cui non esiste alcuna copia da
migrare: erano già rotti sul sito originale.

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

## Layout e template

```
layouts/
├── _default/{baseof,single,list}.html
├── index.html                 → home: elenco notizie da novita/ (paginato) + sidebar
└── partials/
    ├── head.html
    ├── header.html            → .site-header__hero (immagine+titolo) + .navbar separati
    ├── footer.html            → colonne footer + icone social (Genericons)
    ├── sidebar-scheda.html    → widget reali, Archivi/Categorie come link (vedi sopra)
    └── post-list-item.html
```

Il menu è definito in `hugo.toml` sotto `[[menu.main]]`, ricostruito dal menu reale di
WordPress (vedi `CLAUDE.md`).

## Foglio di stile

Un unico file, `static/css/style.css`, con i token di design come custom property CSS in
`:root`. Nessun preprocessore richiesto.

## Provare in locale

```sh
hugo server -D          # http://localhost:1313/
hugo --gc --minify      # build di produzione
```

Validato: 126 pagine generate (72 dal contenuto reale + sezioni/tassonomie/paginazione
automatiche — incluse le 11 pagine di archivio annuale e le 6 di categoria), 0 errori,
71 alias verso i vecchi URL WordPress (`/home/...`) funzionanti.

## Prossimi passi consigliati

1. Migrare gli allegati scaricabili non ancora referenziati da nessun contenuto reale
   (nello `uploads/` originale restano ~130MB di file non copiati perché non citati in
   nessuna pagina/post pubblicato).
2. Configurare redirect 301 lato server (oltre agli `aliases:` già generati) quando il
   sito va in produzione, per il pieno beneficio SEO.
3. Se servono email meno esposte agli scraper rispetto al semplice `mailto:`, valutare
   una piccola funzione JS che ricostruisce l'indirizzo a runtime.
