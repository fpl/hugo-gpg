#!/usr/bin/env python3
"""Migra i contenuti reali da WordPress (DB importato nel container gpg-mysql-tmp)
verso content/ in questo repo Hugo. Vedi CLAUDE.md per il contesto completo.

Uso:
    python3 scripts/wp_to_hugo.py

Richiede: docker (o alias podman) con il container "gpg-mysql-tmp" attivo e il
database "gpg" già importato dal dump UpdraftPlus; il binario "pandoc" in PATH.
Nessuna dipendenza pip: solo stdlib + subprocess.
"""
import hashlib
import json
import re
import subprocess
import sys
import shutil
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
STATIC_UPLOADS = REPO / "static" / "images" / "uploads"
WP_UPLOADS = REPO.parent / "home" / "wp-content" / "uploads"
STATIC_DOWNLOADS = REPO / "static" / "downloads"
WP_DOWNLOADS = REPO.parent / "home" / "downloads"

MYSQL = ["docker", "exec", "-i", "gpg-mysql-tmp", "mysql", "-uroot", "-ptemppass", "-N", "-B", "gpg"]

# --- protezione delle modifiche manuali sui file generati ---------------------
# Stesso meccanismo e stesso file di manifest di scripts/old_to_hugo.py (i due
# script scrivono nello stesso albero content/): se un file generato viene
# modificato a mano dopo l'ultima esecuzione (es. per correggere un layout che
# pandoc rende male), un rilancio dello script NON lo sovrascrive in silenzio.
# Salva una copia della versione manuale in manual-backups/ e segnala lo skip;
# passa --force per sovrascrivere comunque.
MANIFEST_PATH = REPO / ".content-manifest.json"
MANUAL_BACKUPS = REPO / "manual-backups"
FORCE_OVERWRITE = "--force" in sys.argv
_manifest: dict[str, str] = (
    json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
)
skipped_manual: list[str] = []


def safe_write_text(dest: Path, content: str) -> bool:
    """Ritorna True se ha scritto, False se ha saltato per modifica manuale."""
    rel = dest.relative_to(REPO).as_posix()
    if dest.exists() and not FORCE_OVERWRITE:
        current = dest.read_text(encoding="utf-8")
        known_hash = _manifest.get(rel)
        current_hash = hashlib.sha256(current.encode("utf-8")).hexdigest()
        if known_hash is not None and current_hash != known_hash:
            backup = MANUAL_BACKUPS / dest.relative_to(REPO / "content")
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text(current, encoding="utf-8")
            skipped_manual.append(rel)
            print(f"SALTATO (modificato a mano dopo l'ultima generazione): {rel}"
                  f" -- copia della versione attuale in {backup.relative_to(REPO)}")
            return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    _manifest[rel] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    print(f"scritto {rel}")
    return True


def save_manifest():
    MANIFEST_PATH.write_text(json.dumps(_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if skipped_manual:
        print("\n== File con modifiche manuali non sovrascritti (--force per forzare) ==")
        for rel in skipped_manual:
            print(f"- {rel}")

# --- ID pagina WP -> percorso content/ Hugo -----------------------------------
# Mappa scritta a mano dalla gerarchia reale (vedi ricognizione in sessione):
# la gerarchia ha eccezioni (es. Cavità artificiali, pagina di primo livello nel
# DB ma sezione figlia di esplorazioni/ nel menu e nello scaffold) che una regola
# generica su post_parent non catturerebbe correttamente.
PAGE_MAP = {
    10: "chi-siamo/_index.md",
    12: "pubblicazioni/_index.md",
    14: "corsi/_index.md",
    16: "esplorazioni/_index.md",
    18: "eventi/_index.md",
    20: "museo/_index.md",
    42: "ambiente/_index.md",
    125: "esplorazioni/cavita-artificiali.md",
    28: "chi-siamo/statuto.md",
    192: "chi-siamo/consiglio-direttivo.md",
    219: "chi-siamo/contatti.md",
    130: "pubblicazioni/il-primo-convegno-regionale-di-speleologia-pugliese.md",
    136: "pubblicazioni/il-xv-congresso-nazionale-di-speleologia.md",
    142: "pubblicazioni/secondo-convegno-regionale-di-speleologia.md",
    153: "pubblicazioni/il-terzo-convegno-di-speleologia-pugliese-spelaion.md",
    157: "pubblicazioni/primo-convegno-regionale-di-speleologia-in-cavita-artificiali.md",
    161: "pubblicazioni/i-quaderni-di-speleologia-meridionale.md",
    267: "corsi/il-xxxviii-corso-di-speleologia-di-primo-livello.md",
    334: "corsi/il-xli-corso-di-speleologia-di-primo-livello.md",
    403: "corsi/il-xliii-corso-di-speleologia-di-primo-livello.md",
    552: "corsi/il-45-corso-di-speleologia-di-primo-livello.md",
    596: "corsi/il-46-corso-di-speleologia-di-primo-livello.md",
    697: "corsi/il-48-corso-di-speleologia-di-primo-livello.md",
    750: "corsi/49-corso-di-speleologia.md",
    777: "corsi/50-corso-di-speleologia.md",
    823: "corsi/51-corso-di-speleologia.md",
    105: "corsi/il-xxxvii-corso-di-speleologia-di-primo-livello.md",
    67: "esplorazioni/nazionali/_index.md",
    88: "esplorazioni/internazionali/_index.md",
    167: "eventi/tavola-rotonda-acque-del-terzo-millennio.md",
    305: "eventi/discesa-su-teleferica-della-befana.md",
    368: "eventi/settimana-del-pianeta-terra.md",
    503: "eventi/una-mostra-fotografica-storica-sulle-grotte-nel-cuore-di-castellana.md",
    181: "museo/chi-era-franco-anelli.md",
    204: "esplorazioni/nazionali/progetto-impalata.md",
    206: "esplorazioni/nazionali/progetto-grotta-del-dragone.md",
    314: "esplorazioni/nazionali/progetto-catasto-delle-grotte-e-delle-cavita-artificiali-2010.md",
    319: "esplorazioni/nazionali/progetto-catasto-delle-grotte-e-delle-cavita-artificiali.md",
    328: "esplorazioni/nazionali/programma-attivita-speleologica-autunno-inverno-2006-2007.md",
}

# ID pagina WP -> stesso percorso content/, per pagine il cui CONTENUTO non
# viene più generato da questo script (rimosse da PAGE_MAP) ma il cui vecchio
# URL WP deve continuare a risolvere (old_path_map/alias), perché altro
# contenuto reale le linka ancora con un href assoluto /home/....
#
# - 49 (bollettini-puglia-grotte/_index.md): ora una griglia CSS con
#   shortcode {{< bollettino-cover >}} scritta a mano (vedi README.md,
#   "Layout e template"), non più il contenuto grezzo dal DB -- una
#   pipe-table con newline incorporate nelle celle che rompeva il parser di
#   goldmark, il bug originale segnalato dall'utente.
# - 52/54 (bollettino-1984/1985): generate esclusivamente da
#   scripts/old_to_hugo.py --bollettini, per uniformità di formato con le
#   altre 9 annate.
#
# In tutti e tre i casi, lasciarle in PAGE_MAP le faceva rigenerare e
# sovrascrivere silenziosamente ad ogni rilancio di questo script (bug reale,
# scoperto già committato nel repo). Rimuoverle da PAGE_MAP senza tenerle qui,
# però, romperebbe old_path_map per chiunque le linki ancora dal vecchio
# URL -- da cui questa mappa separata, usata SOLO per costruire
# old_path_map/flat_page_map, mai per scrivere contenuto.
MANUAL_PAGES = {
    49: "pubblicazioni/bollettini-puglia-grotte/_index.md",
    52: "pubblicazioni/bollettini-puglia-grotte/bollettino-1984.md",
    54: "pubblicazioni/bollettini-puglia-grotte/bollettino-1985.md",
}

# Qualunque link interno assoluto (immagine, pagina, allegato) verso il vecchio
# sito, con o senza dominio esplicito davanti: WordPress girava nel sotto-percorso
# /home/ (vedi ABSPATH nel dump), quindi anche i link *relativi al dominio* hanno
# questo prefisso.
INTERNAL_RE = re.compile(
    r"(?:https?://(?:www\.)?gruppopugliagrotte\.it)?/home/([^\s\"'\)>]+)"
)

referenced_uploads: set[str] = set()
referenced_downloads: set[str] = set()
warnings: list[str] = []


def uploads_relpath_from_guid(guid: str) -> str | None:
    m = re.search(r"wp-content/uploads/(.+)$", guid)
    return urllib.parse.unquote(m.group(1)) if m else None


def new_permalink(rel_path: str) -> str:
    """Converte un percorso content/ (es. 'corsi/foo.md') nel permalink Hugo
    corrispondente ('/corsi/foo/'), assumendo le pretty URL di default (nessun
    override 'url:' nel front matter, non usato in questo scaffold)."""
    if rel_path.endswith("/_index.md"):
        return "/" + rel_path[: -len("_index.md")]
    return "/" + rel_path[: -len(".md")] + "/"


def sql_rows(query: str) -> list[list[str]]:
    # Attenzione: capture_output+text=True applicherebbe la traduzione
    # universal-newline di Python, che converte anche i singoli byte \r
    # (presenti senza escape in alcuni contenuti reali, mischiati a \n
    # letterali già escapati da mysql) in \n, creando righe di record
    # fittizie. Si decodificano i byte grezzi a mano per evitarlo.
    r = subprocess.run(MYSQL + ["-e", query], capture_output=True)
    if r.returncode != 0:
        sys.exit(f"Errore MySQL: {r.stderr.decode('utf-8', 'replace')}")
    stdout = r.stdout.decode("utf-8")
    rows = []
    for line in stdout.split("\n"):
        if line == "":
            continue
        rows.append([unescape(f) for f in line.split("\t")])
    return rows


def unescape(s: str) -> str | None:
    if s == r"\N":
        return None
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nc = s[i + 1]
            out.append({"n": "\n", "t": "\t", "\\": "\\", "0": "\0"}.get(nc, nc))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def rewrite_internal_links(text: str, old_path_map: dict[str, str],
                            flat_page_map: dict[str, str],
                            attachments_by_name: dict[str, str]) -> str:
    """Riscrive ogni link assoluto al vecchio sito (/home/...) verso il
    percorso Hugo corrispondente:
    - wp-content/uploads/...  -> /images/uploads/... (copiato più avanti)
    - downloads/...           -> /downloads/...      (copiato più avanti)
    - percorso di una pagina/post reale (da old_path_map, la stessa mappa
      usata per generare gli `aliases:`) -> il suo permalink Hugo
    - link "piatto" a una pagina nidificata, cioè senza il prefisso di
      sezione (es. /home/49-corso-di-speleologia/ invece del reale
      /home/corsi/49-corso-di-speleologia/): capita nei contenuti reali,
      probabilmente link scritti a mano prima che la pagina fosse spostata
      sotto una sezione; risolto per slug via flat_page_map
    - pagina-allegato di WordPress (es. /home/<post>/<slug-allegato>/, un
      formato che WP genera per mostrare un file caricato) -> risolta per
      slug dell'allegato nell'attachment map, come se fosse un'immagine
    Qualunque cosa non rientri in questi casi viene lasciata invariata e
    segnalata: sono per lo più link a un sito pre-WordPress ancora più
    vecchio (pagine .htm sotto un'altra struttura), già rotti sul sito
    originale e per cui non abbiamo alcuna copia da migrare.
    """

    def repl(m):
        rest = urllib.parse.unquote(m.group(1))

        if rest.startswith("wp-content/uploads/"):
            rel = rest[len("wp-content/uploads/"):]
            referenced_uploads.add(rel)
            return "/images/uploads/" + rel

        if rest.startswith("downloads/"):
            fname = rest[len("downloads/"):]
            referenced_downloads.add(fname)
            return "/downloads/" + fname

        key = ("/home/" + rest).rstrip("/")
        if key in old_path_map:
            return old_path_map[key]

        slug = rest.rstrip("/").split("/")[-1]
        if slug in flat_page_map:
            return flat_page_map[slug]

        guid = attachments_by_name.get(slug)
        if guid:
            rel = uploads_relpath_from_guid(guid)
            if rel:
                referenced_uploads.add(rel)
                return "/images/uploads/" + rel

        warnings.append(f"link interno non risolto, lasciato invariato: {m.group(0)}")
        return m.group(0)

    return INTERNAL_RE.sub(repl, text)


# Link esterni (fuori dal vecchio dominio del sito) il cui percorso profondo
# non esiste più, verificato via HTTP il 2026-08-12: il dominio stesso è
# ancora attivo, quindi si riscrive verso la sua radice invece di lasciare un
# link rotto o di indovinare un percorso sostitutivo specifico. Ordinate per
# lunghezza decrescente della chiave: una sostituzione testuale semplice deve
# gestire prima gli URL più lunghi, altrimenti un URL più corto che ne è
# prefisso (es. la home di ssi.speleo.it rispetto a ssi.speleo.it/index.html)
# la intercetterebbe per primo e romperebbe il match del più lungo.
EXTERNAL_LINK_REWRITE = {
    "http://www.speleo.it/site/index.php/notizie/145-newsletter/ssi-news-6/1120-animale-grotta-2021": "https://www.speleo.it/",
    "http://www.fscampania.it/alburni/index.htm": "http://www.fscampania.it/",
    "http://www.fspuglia.it/catastogotte_elenco.html": "http://www.fspuglia.it/",
    "http://www.ssi.speleo.it/index.html": "https://www.speleo.it/",
    "http://www.ssi.speleo.it/": "https://www.speleo.it/",
    "http://ssi.speleo.it/": "https://www.speleo.it/",
    # booking.grottedicastellana.it non risolve più; il dominio principale è
    # ancora attivo e la home espone comunque le informazioni di prenotazione.
    "http://booking.grottedicastellana.it/": "https://www.grottedicastellana.it/",
    # Il vecchio OPAC "BookMarkWeb" della Biblioteca "Franco Anelli" (CIDS-SSI,
    # Bologna) non esiste più: il catalogo è confluito nel catalogo unico
    # "Speleoteca" (~20 biblioteche speleologiche italiane). home-lib=10 filtra
    # sulla "Biblioteca Gruppo Puglia Grotte" (372 titoli, verificato) proprio
    # come il link originale era pensato a mostrare il fondo del Gruppo Puglia
    # Grotte, non il catalogo generico di Bologna. Segnalato dall'utente +
    # verificato via ricerca web il 2026-08-12. &amp; letterale perché pandoc
    # lascia l'attributo href intatto così com'è nel DB.
    "http://bmw06.comperio.it/bmw2/speleoteca/opac.php?screen=homepage&amp;loc=S&amp;osc=homepage&amp;orderby=Autore":
        "https://speleoteca.biblioteche.it/opac/search/lst?home-lib=10&q=",
}


def rewrite_external_links(text: str) -> str:
    for old, new in sorted(EXTERNAL_LINK_REWRITE.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(old, new)
    return text


# Link assoluti al vecchio dominio FUORI da /home/: puntano alla radice del
# sito pre-WordPress (es. storiagpg.htm, museo.htm, immagini in images/...),
# non allo stesso spazio /home/ che INTERNAL_RE già gestisce. Questo script
# non converte da solo quelle pagine (lo fa scripts/old_to_hugo.py, che scrive
# la mappa completa risultante in .link-rewrite.json dopo ogni fase): qui si
# legge quella mappa e si sostituisce il vecchio URL assoluto col permalink
# Hugo corrispondente. Se .link-rewrite.json manca o non contiene ancora
# quella voce, il link resta invariato e viene segnalato in warnings (mai
# lasciato in silenzio come falso link "vivo" verso il vecchio dominio).
OLD_DOMAIN_RE = re.compile(
    r'https?://(?:www\.)?gruppopugliagrotte\.it/(?!home/)([^\s"\'\)>]+)'
)
OLD_LINK_REWRITE_PATH = REPO / ".link-rewrite.json"
OLD_LINK_REWRITE: dict[str, str] = (
    json.loads(OLD_LINK_REWRITE_PATH.read_text(encoding="utf-8"))
    if OLD_LINK_REWRITE_PATH.exists() else {}
)


def rewrite_old_domain_links(text: str) -> str:
    def repl(m):
        rest = urllib.parse.unquote(m.group(1))
        key = rest.split("?")[0].split("#")[0]
        if key in OLD_LINK_REWRITE:
            return OLD_LINK_REWRITE[key]
        warnings.append(
            f"link al vecchio sito (fuori da /home/) non risolto in .link-rewrite.json, "
            f"lasciato invariato: {m.group(0)}"
        )
        return m.group(0)
    return OLD_DOMAIN_RE.sub(repl, text)


# images/on.gif è l'icona di rollover "acceso", un bullet decorativo dentro
# link con ancora reale sulla stessa pagina -- non contenuto (stessa
# classificazione di strip_nav_icons in scripts/old_to_hugo.py, che per questo
# la esclude apposta da DIRECT_ASSETS). Va tolta dall'<img>, non risolta come
# link: gestita qui perché è l'unica pagina proveniente da WordPress (non da
# old/) a referenziarla ancora.
NAV_ICON_IMG_RE = re.compile(
    r'<img\b[^>]*\bsrc="https?://(?:www\.)?gruppopugliagrotte\.it/images/on\.gif"[^>]*/?>\s*',
    re.I,
)


def strip_known_nav_icons(text: str) -> str:
    return NAV_ICON_IMG_RE.sub("", text)


def preprocess_shortcodes(html: str, attachments: dict[str, str]) -> str:
    """Sostituisce [caption], [gallery], [embed] con placeholder testuali che
    pandoc non toccherà, da rigenerare in markdown dopo la conversione."""

    def caption_repl(m):
        inner = m.group(1)
        img_match = re.search(r"<img[^>]*>", inner)
        img = img_match.group(0) if img_match else ""
        text = inner[img_match.end():].strip() if img_match else inner.strip()
        text = re.sub(r"^[\s\-–]+", "", text)
        return f"<figure>{img}<figcaption>{text}</figcaption></figure>"

    html = re.sub(r"\[caption[^\]]*\](.*?)\[/caption\]", caption_repl, html, flags=re.S)

    def gallery_repl(m):
        ids = re.search(r'ids="([^"]+)"', m.group(0))
        if not ids:
            return ""
        imgs = []
        for aid in ids.group(1).split(","):
            guid = attachments.get(aid.strip())
            if guid:
                imgs.append(f'<img src="{guid}">')
            else:
                warnings.append(f"attachment id {aid} non trovato per [gallery]")
        # Niente shortcode Hugo dedicato: con solo 7 usi nel sito reale, una
        # semplice sequenza di immagini in un div (stile via style.css) basta
        # e non introduce un template da mantenere per un caso così raro.
        return '\n\n<div class="wp-gallery">\n' + "\n".join(imgs) + "\n</div>\n\n"

    html = re.sub(r"\[gallery[^\]]*\]", gallery_repl, html)
    html = re.sub(r"\[embed\](.*?)\[/embed\]", lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', html)
    return html


def html_to_md(html: str) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "html", "-t", "gfm", "--wrap=preserve"],
        input=html, capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(f"Errore pandoc: {r.stderr}")
    return r.stdout.strip()


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def write_content(rel_path: str, title: str, body_html: str, attachments,
                   old_path_map: dict[str, str], flat_page_map: dict[str, str],
                   attachments_by_name: dict[str, str],
                   date: str | None = None, excerpt: str | None = None,
                   aliases: list[str] | None = None, categories: list[str] | None = None):
    dest = CONTENT / rel_path

    fm = ["---", f"title: {yaml_str(title)}"]
    if date:
        fm.append(f"date: {date}")
        # Tassonomia "anno" (vedi hugo.toml: [taxonomies] anno = "anni"): il
        # campo nel front matter deve chiamarsi come il valore PLURALE della
        # config ("anni"), non come la chiave singolare ("anno") — lo stesso
        # vale per "categories" qui sopra, che infatti già funzionava.
        fm.append(f"anni: {yaml_str(date.split('-')[0])}")
    if excerpt:
        fm.append(f"description: {yaml_str(strip_tags(excerpt))}")
    if categories:
        fm.append("categories:")
        for c in categories:
            fm.append(f"  - {yaml_str(c)}")
    if aliases:
        fm.append("aliases:")
        for a in aliases:
            fm.append(f'  - {yaml_str(a)}')
    fm.append("---")

    if body_html and body_html.strip():
        pre = preprocess_shortcodes(body_html, attachments)
        md = html_to_md(pre)
        md = rewrite_internal_links(md, old_path_map, flat_page_map, attachments_by_name)
        md = strip_known_nav_icons(md)
        md = rewrite_old_domain_links(md)
        md = rewrite_external_links(md)
    else:
        md = ("<!-- TODO migrazione: contenuto assente anche nella pagina originale del\n"
              "     sito, verificato nel dump del database (non è un errore di\n"
              "     conversione). Non inventare testo qui. -->")
        warnings.append(f"{rel_path}: post_content vuoto nel DB originale, scritto placeholder esplicito")

    safe_write_text(dest, "\n".join(fm) + "\n\n" + md + "\n")


def build_old_url(pid: int, pages_by_id: dict) -> str:
    parts = []
    cur = pid
    while cur and cur in pages_by_id:
        parts.append(pages_by_id[cur]["post_name"])
        cur = pages_by_id[cur]["post_parent"]
    return "/home/" + "/".join(reversed(parts)) + "/"


def copy_referenced(refs: set[str], src_root: Path, dst_root: Path, label: str):
    copied, missing_files = 0, []
    for rel in sorted(refs):
        src = src_root / rel
        dst = dst_root / rel
        if not src.exists():
            missing_files.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    print(f"copiati {copied} file in {dst_root.relative_to(REPO)}/")
    for f in missing_files:
        warnings.append(f"{label} referenziato ma non trovato: {f}")


def main():
    print("== Query attachment ==")
    attachments, attachments_by_name = {}, {}
    for aid, name, guid in sql_rows("SELECT ID, post_name, guid FROM wp_posts WHERE post_type='attachment'"):
        attachments[aid] = guid
        attachments_by_name[name] = guid

    print("== Query pagine ==")
    # Unione con MANUAL_PAGES: servono comunque i loro record (post_name,
    # post_parent) per calcolare old_path_map/flat_page_map -- vedi sotto --
    # anche se il contenuto non si riscrive più per queste pagine.
    all_page_ids = set(PAGE_MAP) | set(MANUAL_PAGES)
    ids_csv = ",".join(str(i) for i in all_page_ids)
    pages_by_id = {}
    for pid, title, name, parent, excerpt, content in sql_rows(
        f"SELECT ID, post_title, post_name, post_parent, post_excerpt, post_content "
        f"FROM wp_posts WHERE ID IN ({ids_csv})"
    ):
        pages_by_id[int(pid)] = {
            "title": title, "post_name": name, "post_parent": int(parent),
            "excerpt": excerpt, "content": content,
        }

    missing = all_page_ids - set(pages_by_id)
    if missing:
        sys.exit(f"Pagine mancanti nel DB rispetto alla mappa: {missing}")

    print("== Query categorie dei post ==")
    categories_by_post: dict[str, list[str]] = {}
    for pid, cat_name in sql_rows(
        "SELECT tr.object_id, t.name FROM wp_term_relationships tr "
        "JOIN wp_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id "
        "JOIN wp_terms t ON tt.term_id = t.term_id "
        "WHERE tt.taxonomy='category' AND t.slug != 'uncategorized'"
    ):
        categories_by_post.setdefault(pid, []).append(cat_name)

    print("== Query post (novita) ==")
    posts = sql_rows(
        "SELECT ID, post_title, post_name, post_date, post_excerpt, post_content "
        "FROM wp_posts WHERE post_type='post' AND post_status='publish'"
    )

    # Mappa vecchio percorso WP (lo stesso testo scritto in aliases:) -> nuovo
    # permalink Hugo, costruita per intero PRIMA di scrivere i file: serve a
    # riscrivere i link interni che compaiono nel corpo di qualunque pagina o
    # post, non solo i propri.
    old_path_map: dict[str, str] = {}
    flat_page_map: dict[str, str] = {}
    for pid, rel_path in {**PAGE_MAP, **MANUAL_PAGES}.items():
        old = build_old_url(pid, pages_by_id).rstrip("/")
        old_path_map[old] = new_permalink(rel_path)
        flat_page_map[pages_by_id[pid]["post_name"]] = new_permalink(rel_path)
    for pid, title, name, date, excerpt, content in posts:
        old_path_map[f"/home/{name}"] = f"/novita/{name}/"

    for pid, rel_path in PAGE_MAP.items():
        p = pages_by_id[pid]
        alias = build_old_url(pid, pages_by_id)
        write_content(rel_path, p["title"], p["content"], attachments,
                      old_path_map, flat_page_map, attachments_by_name,
                      excerpt=p["excerpt"], aliases=[alias])

    for pid, title, name, date, excerpt, content in posts:
        rel_path = f"novita/{name}.md"
        write_content(rel_path, title, content, attachments,
                      old_path_map, flat_page_map, attachments_by_name,
                      date=date.split(" ")[0], excerpt=excerpt,
                      aliases=[f"/home/{name}/"],
                      categories=categories_by_post.get(pid))

    print(f"\n{len(PAGE_MAP)} pagine + {len(posts)} post elaborati.")

    print("\n== Copia allegati referenziati ==")
    copy_referenced(referenced_uploads, WP_UPLOADS, STATIC_UPLOADS, "allegato")
    copy_referenced(referenced_downloads, WP_DOWNLOADS, STATIC_DOWNLOADS, "download")

    save_manifest()

    if warnings:
        print("\n== Avvisi ==", file=sys.stderr)
        for w in warnings:
            print(f"- {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
