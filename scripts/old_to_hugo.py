#!/usr/bin/env python3
"""Fase 1 dell'integrazione di old/www.gruppopugliagrotte.it (sito pre-WordPress,
copia statica completa fornita dall'utente) nel sito Hugo. Vedi il piano
"Integrazione old/" e CLAUDE.md per il contesto completo.

Migra SOLO le pagine e gli asset di old/ già citati da link reali (assoluti,
oggi rotti) nel contenuto Hugo già migrato da WordPress — non l'intero archivio
storico (949 pagine), per decisione esplicita dell'utente. Una Fase 2 successiva,
non coperta da questo script, potrà ampliare l'archivio dopo revisione.

Uso:
    python3 scripts/old_to_hugo.py

Nessuna dipendenza pip: solo stdlib + subprocess (pandoc). Le pagine sorgente
sono in ISO-8859-1 (verificato con `file`), decodificate come tali prima di
passarle a pandoc.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content" / "archivio-storico"
STATIC_LEGACY = REPO / "static" / "archivio-storico" / "legacy"
OLD_ROOT = REPO.parent / "old" / "www.gruppopugliagrotte.it"

warnings: list[str] = []

# --- protezione delle modifiche manuali sui file generati ---------------------
# Lo script è idempotente per design (rilancio = rigenerazione totale), ma
# questo entra in conflitto con modifiche fatte a mano su un file già generato
# (es. correggere un layout che pandoc rende male): un rilancio le
# sovrascriverebbe in silenzio. .content-manifest.json ricorda l'hash
# dell'ULTIMO contenuto scritto DA QUESTO SCRIPT per ogni file; se l'hash
# attuale su disco non corrisponde, il file è stato toccato a mano nel
# frattempo e NON viene sovrascritto (si salva una copia in manual-backups/ e
# si segnala). Passa --force per sovrascrivere comunque.
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

# --- href/src (root-relative rispetto a old/www.gruppopugliagrotte.it/) --------
# -> permalink Hugo assoluto (per le 16 pagine/asset già migrati in questa fase)
# oppure percorso static/ (per gli asset copiati as-is). Href non presenti qui,
# se interni a old/, vengono spogliati del link (testo semplice) perché la
# pagina di destinazione non fa parte di questa fase — non lasciamo link rotti.
LINK_REWRITE = {
    "museo.htm": "/archivio-storico/museo/",
    "storiagpg.htm": "/archivio-storico/storiagpg/",
    "pugliagrotte.htm": "/archivio-storico/pugliagrotte/",
    "rivistaNS.htm": "/archivio-storico/rivista-grotte-e-dintorni/",
    "pubb_ita.htm": "/archivio-storico/pubblicazioni/",
    "esplo_ita.htm": "/archivio-storico/esplorazione-e-ricerca/",
    "speleoartifi.htm": "/archivio-storico/speleologia-artificiale/",
    "festival.htm": "/archivio-storico/festival-avventura/",
    "cuba.htm": "/archivio-storico/cuba/",
    "albania.htm": "/archivio-storico/albania/",
    "speleonight.htm": "/archivio-storico/speleonight/",
    "eventi/convegno2007.htm": "/archivio-storico/convegno-2007/",
    "eventi/spelaion2011.htm": "/archivio-storico/spelaion-2011/",
    # Le 8 sottopagine (chi/cosa/dove/come/programma/contatti/download/staff)
    # sono state accorpate in un'unica pagina piatta (vedi commento su
    # spelaion-2011 in PAGES sopra): un link a una di queste risolve comunque
    # alla pagina consolidata, non spogliato come "non migrato".
    "eventi/spelaion2011/chi.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/cosa.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/dove.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/come.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/programma.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/contatti.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/download.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/staff.htm": "/archivio-storico/spelaion-2011/",
    "eventi/spelaion2011/AttiSpelaion2011.pdf": "/archivio-storico/legacy/eventi/spelaion2011/AttiSpelaion2011.pdf",
    "eventi/spelaion2011/CSSpelaionFinale.pdf": "/archivio-storico/legacy/eventi/spelaion2011/CSSpelaionFinale.pdf",
    "eventi/spelaion2011/CSSpelaion.pdf": "/archivio-storico/legacy/eventi/spelaion2011/CSSpelaion.pdf",
    "eventi/spelaion2011/FotoAlbum.pdf": "/archivio-storico/legacy/eventi/spelaion2011/FotoAlbum.pdf",
    "eventi/spelaion2011/Spelaion2011-Iscrizione.doc": "/archivio-storico/legacy/eventi/spelaion2011/Spelaion2011-Iscrizione.doc",
    "eventi/spelaion2011/Spelaion2011-liberatoria.doc": "/archivio-storico/legacy/eventi/spelaion2011/Spelaion2011-liberatoria.doc",
    "eventi/spelaion2011/Spelaion2011-SchedaInformativa.doc": "/archivio-storico/legacy/eventi/spelaion2011/Spelaion2011-SchedaInformativa.doc",
    "eventi/spelaion2011/Spelaion2011-UltimaCircolare.pdf": "/archivio-storico/legacy/eventi/spelaion2011/Spelaion2011-UltimaCircolare.pdf",
    "eventi/spelaion2011/SSISpelaion2011.pdf": "/archivio-storico/legacy/eventi/spelaion2011/SSISpelaion2011.pdf",
    "eventi/images/spelaion2011/logoexport.jpg": "/archivio-storico/legacy/eventi/images/spelaion2011/logoexport.jpg",
    "attivi/programma0607.htm": "/archivio-storico/programma-2006-2007/",
    "convreg/programma.htm": "/archivio-storico/iii-convegno-speleologia-pugliese/",
    "corso/corsoalburni.htm": "/archivio-storico/corso-alburni/",
    "esplorazioni/speleoartifi/depositocarrino.htm": "/archivio-storico/deposito-carrino/",
    "santomas/chi.htm": "/archivio-storico/progetto-santo-tomas/",
    "santomas/perche.htm": "/archivio-storico/progetto-santo-tomas/",
    "santomas/dove.htm": "/archivio-storico/progetto-santo-tomas/",
    # santomas/index.htm non è una pagina di contenuto: è solo il frameset di
    # rilevamento risoluzione schermo (redirect JS a index1024.htm), verificato
    # aprendo il sorgente -- nessun testo proprio da migrare. Punta comunque a
    # /progetto-santo-tomas/, la pagina reale a cui i link con questo href si
    # riferivano nell'intento (citata come "la spedizione Santo Tomás").
    "santomas/index.htm": "/archivio-storico/progetto-santo-tomas/",
    # old-index.htm non esiste in old/ con questo nome esatto (probabile refuso
    # nel post WP originale, verificato: candidati più vicini sono index.htm/
    # index_ita.htm/index1024.htm, tutte pagine di puro chrome/redirect senza
    # testo proprio). L'intento del link ("guarda il vecchio sito") è coperto
    # meglio dalla sezione che lo sostituisce.
    "old-index.htm": "/archivio-storico/",
    "esplorazioni/speleoartifi/Catasto.pdf": "/archivio-storico/legacy/esplorazioni/speleoartifi/Catasto.pdf",
    "GruppoPugliaGrotteCatalogoBiblioteca2013.zip": "/archivio-storico/legacy/GruppoPugliaGrotteCatalogoBiblioteca2013.zip",
}

# (source_rel, src come scritto nel sorgente) -> percorso corretto relativo a
# OLD_ROOT. speleonight.htm (radice) ha due <img src> rimasti rotti già sul
# sito originale (puntano a "images/speleonight...", inesistente a livello
# radice); i file reali esistono sotto eventi/images/... -- verificato che
# sono davvero le stesse immagini (nome e soggetto coincidono con la pagina
# gemella eventi/speleonight.htm, che le referenzia correttamente).
IMAGE_SRC_OVERRIDES = {
    ("speleonight.htm", "images/speleonight.jpg"): "eventi/images/speleonight.jpg",
    ("speleonight.htm", "images/speleonight/mariangela.jpg"): "eventi/images/speleonight/mariangela.jpg",
}

# (source_rel) -> (testo da cercare, sostituzione) applicata al sorgente grezzo
# PRIMA dell'estrazione. Corregge errori di markup genuini del sito originale
# che romperebbero il bilanciamento <td>/</td> (contatore verificato con
# grep: 41 <td> contro 40 </td> in questo file) -- non è contenuto alterato,
# solo un tag di chiusura mancante nell'HTML sorgente.
SOURCE_PATCHES = {
    "eventi/falo2007.htm": (
        '<td width="100%" colspan="2" align="center"><img src="images/falo/2007/9.jpg" hspace="5" vspace="5" border="1" style="border-color: black;" alt="Foto di Marilena Rodi">\n</tr>',
        '<td width="100%" colspan="2" align="center"><img src="images/falo/2007/9.jpg" hspace="5" vspace="5" border="1" style="border-color: black;" alt="Foto di Marilena Rodi"></td>\n</tr>',
    ),
}

# (percorso content/archivio-storico/<slug>.md) -> (testo, sostituzione)
# applicata al Markdown GENERATO, dopo la scrittura. storiagpg.htm ha un
# apice solitario rimasto nell'HTML originale (probabile refuso di editing,
# senza virgoletta di chiusura in tutto il paragrafo) che pandoc riporta
# come riga a sé; non è contenuto, va tolto.
POST_FIXUPS = {
    "storiagpg.md": (
        "Forte dell'esperienza di anni, infatti, il Gruppo Puglia Grotte ha organizzato:  \n\"\n\n- I Convegno",
        "Forte dell'esperienza di anni, infatti, il Gruppo Puglia Grotte ha organizzato:\n\n- I Convegno",
    ),
}


def apply_post_fixups():
    for rel, (find, repl) in POST_FIXUPS.items():
        path = CONTENT / rel
        text = path.read_text(encoding="utf-8")
        if find not in text:
            sys.exit(f"POST_FIXUPS[{rel}]: testo da sostituire non trovato (contenuto cambiato?)")
        if safe_write_text(path, text.replace(find, repl)):
            print(f"post-fixup applicato a {path.relative_to(REPO)}")

# Pagine da convertire in content/archivio-storico/<slug>.md.
# mode "testo": unisce i blocchi <td class="testo"> di primo livello (non annidati).
# mode "body": nessuna cella "testo" nel sorgente (template "pagina singola" senza
#              chrome di navigazione) -> prende il/i <td> di primo livello col
#              maggior contenuto testuale nel <body>.
PAGES = [
    dict(slug="museo", title="Il Museo Speleologico Franco Anelli",
         sources=["museo.htm"], mode="testo"),
    dict(slug="storiagpg", title="Chi siamo",
         sources=["storiagpg.htm"], mode="testo"),
    dict(slug="pugliagrotte", title="I bollettini Puglia Grotte",
         sources=["pugliagrotte.htm"], mode="testo"),
    dict(slug="rivista-grotte-e-dintorni", title="Il Museo Speleologico Franco Anelli — la rivista Grotte e Dintorni",
         sources=["rivistaNS.htm"], mode="testo"),
    dict(slug="pubblicazioni", title="Pubblicazioni",
         sources=["pubb_ita.htm"], mode="testo"),
    dict(slug="esplorazione-e-ricerca", title="Esplorazione e ricerca",
         sources=["esplo_ita.htm"], mode="testo"),
    dict(slug="speleologia-artificiale", title="Speleologia artificiale",
         sources=["speleoartifi.htm"], mode="testo"),
    dict(slug="festival-avventura", title="L'avventura dell'uomo — Festival del film d'avventura",
         sources=["festival.htm"], mode="body"),
    dict(slug="cuba", title="La Sociedad Espeleologica de Cuba a Castellana-Grotte",
         sources=["cuba.htm"], mode="testo"),
    dict(slug="albania", title="Le spedizioni in Albania",
         sources=["albania.htm"], mode="body"),
    dict(slug="speleonight", title="Speleonight",
         sources=["speleonight.htm"], mode="testo"),
    dict(slug="convegno-2007", title="I Convegno Regionale di Speleologia in Cavità Artificiali — Architetture nel Buio",
         sources=["eventi/convegno2007.htm"], mode="testo"),
    # spelaion-2011: NON più generata qui. eventi/spelaion2011.htm era solo la
    # pagina di copertina; le 8 sottopagine reali linkate dal suo menu (Chi/
    # Cosa/Dove/Come/Programma/Contatti/Download/Staff, in eventi/spelaion2011/)
    # non erano coperte da nessuna fase dello script (struttura a sottocartella,
    # diversa dal solito singolo .htm per evento di EVENTI_FILES) e non sono
    # mai state migrate -- scoperto e colmato a mano in una sessione successiva.
    # Prima ristrutturata in una sezione con 8 sotto-pagine reali (stesso
    # trattamento di iii-convegno-speleologia-pugliese sopra), poi accorpata di
    # nuovo in un'UNICA pagina piatta (content/archivio-storico/spelaion-2011.md)
    # su richiesta esplicita dell'utente: 8 URL separate per pochi paragrafi
    # ciascuna era la stessa impostazione "sito multipagina anni '90" che il
    # resto del sito ha già abbandonato altrove -- niente più nav ad ancore
    # interne (#chi/#cosa/...) ripetuta identica in cima a ogni sottopagina,
    # niente più icona di download per ogni allegato (solo link col titolo).
    dict(slug="programma-2006-2007", title="Programma attività speleologica autunno-inverno 2006-2007",
         sources=["attivi/programma0607.htm"], mode="testo"),
    # iii-convegno-speleologia-pugliese: NON più generata qui. Una sessione
    # precedente l'ha ristrutturata a mano in una sezione con sotto-pagine
    # reali (content/archivio-storico/iii-convegno-speleologia-pugliese/
    # _index.md + risultati.md + immagini.md, quest'ultime due mai prodotte
    # da questo script) -- un rilancio scriverebbe di nuovo un file piatto
    # iii-convegno-speleologia-pugliese.md in conflitto con quella directory
    # (stesso permalink Hugo). Rimossa dalla lista invece di lasciar
    # rigenerare un file orfano: la sezione è ora manutenuta a mano.
    dict(slug="corso-alburni", title="Corso di I livello di Speleologia sui Monti Alburni",
         sources=["corso/corsoalburni.htm"], mode="testo"),
    dict(slug="deposito-carrino", title="Esplorazioni al Deposito Carrino",
         sources=["esplorazioni/speleoartifi/depositocarrino.htm"], mode="testo"),
    dict(slug="progetto-santo-tomas", title="Progetto Santo Tomás — spedizioni speleologiche a Cuba",
         sources=["santomas/chi.htm", "santomas/perche.htm", "santomas/dove.htm"], mode="testo"),
]

# Asset copiati as-is (nessuna conversione), referenziati dal contenuto reale
# già migrato con link assoluti al vecchio dominio.
DIRECT_ASSETS = [
    "esplorazioni/alburni/alburni10febb2012.pdf", "esplorazioni/alburni/alburni12apr2012.pdf",
    "esplorazioni/alburni/alburni16giu2012.pdf", "esplorazioni/alburni/alburni18mar2012.pdf",
    "esplorazioni/alburni/alburni19febb2012.pdf", "esplorazioni/alburni/alburni26febb2012.pdf",
    "esplorazioni/alburni/alburni31mar2012.pdf", "esplorazioni/alburni/alburni7apri2012.pdf",
    "esplorazioni/alburni/alburni8apri2012.pdf", "esplorazioni/alburni/alburnicolorazioni10mar2012.pdf",
    "esplorazioni/alburni/alburnifebb2012.pdf", "esplorazioni/alburni/ProgettoDidatticoAlburniFinale.pdf",
    "esplorazioni/alburni/ProgettoDidatticoAlburni.pdf", "esplorazioni/alburni/PROGETTO_GENTILI_2012.pdf",
    "esplorazioni/alburni/RelazioneAlburn28.04.06.05.2012.pdf",
    "esplorazioni/alburni/CS fine campo Alburni 2012.pdf",
    "esplorazioni/speleoartifi/Catasto.pdf",
    "convreg/images/CassaRuralePetit.jpg", "convreg/images/ComuneCastellana.jpg",
    "convreg/images/GrotteSrl.jpg", "convreg/images/LabInstruments.jpg",
    "convreg/images/LogodefinitivoPiccolo.jpg", "convreg/images/LogoFsp.jpg",
    "convreg/images/ordinegeologi.jpg", "convreg/images/regionepuglia.jpg",
    "convreg/images/scienze.jpg", "convreg/images/SSI.jpg",
    "eventi/images/convegno2007/castellani.jpg", "eventi/images/convegno2007/loghi.jpg",
    "eventi/images/convegno2007/logo.jpg",
    "images/1984_little.jpg", "images/1985_little.jpg", "images/1986_little.jpg",
    "images/1991_little.jpg", "images/1993_little.jpg", "images/1995_little.jpg",
    "images/1996_little.jpg", "images/1999_little.jpg", "images/2001_little.jpg",
    "images/2003_little.jpg", "images/2008_little.jpg",
    "images/anelli.jpg", "images/bro.jpg", "images/convnaz87.jpg",
    "images/convreg1992.jpg", "images/convreg85.jpg",
    # images/on.gif ESCLUSO di proposito: non è contenuto, è l'icona di
    # rollover "acceso" usata come bullet decorativo in link con ancora reale
    # sulla stessa pagina (stessa classificazione già applicata in
    # strip_nav_icons per il resto del sito) -- va tolta dall'<img>, non
    # copiata come asset. Gestita in scripts/wp_to_hugo.py (unica pagina WP
    # che la referenzia).
    "images/q_1985_little.jpg", "images/q_1986_little.jpg", "images/q_1987_little.jpg",
    "images/q_1995_little.jpg",
    "GruppoPugliaGrotteCatalogoBiblioteca2013.zip",
]

# Ogni asset diretto copiato in static/archivio-storico/legacy/<rel> deve avere
# anche una voce in LINK_REWRITE (altrimenti resta "solo copiato": nessun link
# nel contenuto reale punta mai lì). setdefault: non tocca le due voci sopra
# già mappate esplicitamente con lo stesso schema di percorso.
for _asset in DIRECT_ASSETS:
    # .replace(" ", "%20"): "CS fine campo Alburni 2012.pdf" è un nome file
    # reale con spazi. Innocuo nel percorso su disco, ma questo valore finisce
    # anche come URL letterale dentro sintassi Markdown [testo](url) (sia qui
    # sia in scripts/wp_to_hugo.py via .link-rewrite.json): uno spazio nudo lì
    # tronca a metà il link invece di far parte della URL (bug riscontrato e
    # corretto qui).
    LINK_REWRITE.setdefault(_asset, f"/archivio-storico/legacy/{_asset}".replace(" ", "%20"))
del _asset

# LINK_REWRITE completa (Fase 1+2+3) esportata in .link-rewrite.json alla
# radice del repo: scripts/wp_to_hugo.py la legge per risolvere gli stessi
# vecchi link assoluti (fuori da /home/) quando compaiono nel contenuto reale
# proveniente da WordPress, che questo script non tocca mai direttamente.
# Fusa (non sovrascritta) con quanto già presente: le tre fasi si possono
# rilanciare indipendentemente e ognuna aggiunge solo le proprie voci.
LINK_REWRITE_EXPORT_PATH = REPO / ".link-rewrite.json"


def export_link_rewrite():
    existing = (
        json.loads(LINK_REWRITE_EXPORT_PATH.read_text(encoding="utf-8"))
        if LINK_REWRITE_EXPORT_PATH.exists() else {}
    )
    existing.update(LINK_REWRITE)
    LINK_REWRITE_EXPORT_PATH.write_text(
        json.dumps(existing, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


CLASS_ATTR = re.compile(r'class\s*=\s*"([^"]*)"', re.I)
CONTENT_TAGS = ("td", "div")


def extract_class_blocks(html: str, require_class: str | None,
                          tag_names: tuple[str, ...] = CONTENT_TAGS,
                          include_nested: bool = False) -> list[str]:
    """Blocchi <tag>...</tag> di primo livello (non annidati dentro un altro
    blocco già estratto, a meno di include_nested=True), bilanciando la
    profondità del tag stesso -- necessario perché alcune pagine hanno tabelle
    annidate anche dentro le celle di contenuto reale (es. pugliagrotte.htm:
    griglia di anteprime per anno dentro un'unica cella "testo" esterna). Il
    sito usa sia <td class="testo"> (layout a tabelle) sia <div class="testo">
    (pagine con tab JS, es. museo.htm) a seconda della pagina."""
    starts = []
    for tag in tag_names:
        for m in re.finditer(rf"<{tag}\b[^>]*>", html, re.I):
            if require_class:
                cm = CLASS_ATTR.search(m.group(0))
                if not cm or require_class not in cm.group(1).split():
                    continue
            starts.append((m.start(), tag))
    starts.sort()

    used: list[tuple[int, int]] = []
    blocks = []
    for start, tag in starts:
        if not include_nested and any(s <= start < e for s, e in used):
            continue
        token_re = re.compile(rf"<{tag}\b[^>]*>|</{tag}\s*>", re.I)
        depth = 0
        end = None
        open_tag_end = None
        for m in token_re.finditer(html, start):
            if m.group(0).lower().lstrip().startswith(f"</{tag}"):
                depth -= 1
                if depth == 0:
                    end = m.start()
                    break
            else:
                if open_tag_end is None:
                    open_tag_end = m.end()
                depth += 1
        if end is not None:
            used.append((start, end + len(tag) + 3))
            blocks.append(html[open_tag_end:end])
    return blocks


def strip_html_comments(html: str) -> str:
    """Alcune pagine hanno intere gallerie commentate via <!-- ... --> (es.
    eventi/unomattina.htm: una tabella di foto mai caricate su old/, lasciata
    come commento dall'autore originale). pandoc le ignora già in output, ma
    un regex naive su src="...jpg" le troverebbe comunque, generando falsi
    avvisi "asset non trovato" per file che non sono mai stati contenuto
    reale nemmeno sul sito originale."""
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


# Icone .gif decorative/di navigazione ereditate dal vecchio sito (loghi
# "torna alla home", pallini di stato per tab JS con rollover MM_swapImage,
# frecce separatrici, spaziatori trasparenti...), verificate una per una
# guardando il sorgente: non hanno alcun senso -- né visivo né come link --
# su un sito statico moderno. "logo*"/"up*"/"top*" sono prefissi (loghetto.gif,
# logo.gif, upbianco.gif...), il resto sono nomi esatti trovati nel corpus.
NAV_ICON_EXACT = frozenset({
    "loghetto.gif", "gpg.gif", "eventi.gif", "on.gif", "off.gif",
    "arrow.gif", "button.gif", "space.gif",
})
NAV_ICON_PREFIXES = ("logo", "up", "top")
# Eccezione: logo di patrocinio reale (Società Speleologica Italiana), non
# chrome di navigazione -- inizia per "logo" solo per coincidenza nel nome
# del file, va tenuto come gli altri loghi di patrocinio/sponsor.
NAV_ICON_EXCEPTIONS = frozenset({"logossipetit.gif"})

NAV_ICON_IMG = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*/?>', re.I)


def _is_nav_icon(basename: str) -> bool:
    b = basename.lower()
    if b in NAV_ICON_EXCEPTIONS:
        return False
    if b in NAV_ICON_EXACT:
        return True
    return b.endswith(".gif") and b.startswith(NAV_ICON_PREFIXES)


def strip_nav_icons(html: str) -> str:
    """Toglie solo il tag <img>, non un eventuale <a> che lo racchiude: alcune
    di queste icone (es. on.gif) stanno dentro link reali verso ancore della
    STESSA pagina (indice cliccabile di iii-convegno-speleologia-pugliese.md,
    href="#1" ecc.), che devono restare funzionanti col loro testo."""
    def repl(m):
        basename = m.group(1).rsplit("/", 1)[-1]
        return "" if _is_nav_icon(basename) else m.group(0)
    return NAV_ICON_IMG.sub(repl, html)


ABSOLUTE_DIV = re.compile(
    r'<div\b[^>]*style="[^"]*position\s*:\s*absolute[^"]*"[^>]*>(.*?)</div>',
    re.I | re.S,
)


def unwrap_absolute_divs(html: str) -> str:
    """Alcune pagine (template a tab JS tipo museo.htm) hanno <div
    style="position:absolute;..."> annidati DENTRO una cella "testo" già
    estratta (es. rivistaNS.htm: un div con l'indirizzo del museo). Il
    posizionamento assoluto non ha senso in una pagina statica lineare e
    romperebbe il layout se lasciato nell'HTML grezzo che finisce nel
    Markdown -- si toglie il wrapper mantenendo il contenuto."""
    return ABSOLUTE_DIV.sub(r"\1", html)


UTILITY_ICON_RE = re.compile(r"(stampa|chiudi)\.gif", re.I)


TABLE_TOKEN = re.compile(r"<table\b[^>]*>|</table\s*>", re.I)


def _all_table_spans(html: str) -> list[tuple[int, int]]:
    """Tutti gli span <table>...</table> (tag inclusi), a qualunque profondità
    di annidamento -- serve per trovare il widget stampa/chiudi anche quando è
    annidato in coda a una cella di contenuto più grande, non come blocco a sé."""
    spans = []
    for m in re.finditer(r"<table\b[^>]*>", html, re.I):
        start = m.start()
        depth = 0
        for tm in TABLE_TOKEN.finditer(html, start):
            if tm.group(0).lower().lstrip().startswith("</table"):
                depth -= 1
                if depth == 0:
                    spans.append((start, tm.end()))
                    break
            else:
                depth += 1
    return spans


def strip_print_close_widget(html: str) -> str:
    """Il sito originale ripete ovunque un piccolo widget "stampa"/"chiudi
    finestra" (pensato per le pagine aperte in popup via MM_openBrWindow):
    <table><tr><td class="testo"><img .../stampa.gif></td><td
    class="testo"><img .../chiudi.gif></td></tr></table>, spesso annidato in
    coda alla stessa cella del contenuto reale (non un blocco a sé, altrimenti
    l'estrazione per blocchi lo scarterebbe già). Non ha alcun senso su un
    sito statico (non ci sono popup) -- si toglie l'intera tabella."""
    spans = [(s, e) for s, e in _all_table_spans(html)
             if "stampa.gif" in html[s:e].lower() and "chiudi.gif" in html[s:e].lower()]
    # tra tabelle annidate che contengono entrambe le icone, tiene solo le più
    # interne (il widget vero, non un suo antenato più grande).
    minimal = [c for c in spans if not any(c != o and o[0] <= c[0] and c[1] <= o[1] for o in spans)]
    for start, end in sorted(minimal, reverse=True):
        html = html[:start] + html[end:]
    return html


def _testo_extraction(raw: str) -> str | None:
    blocks = extract_class_blocks(raw, require_class="testo")
    return "\n<hr>\n".join(blocks) if blocks else None


def _body_extraction(raw: str) -> str | None:
    body_m = re.search(r"<body[^>]*>(.*)</body>", raw, re.I | re.S)
    body = body_m.group(1) if body_m else raw
    # include_nested=True: alcune pagine (es. corso25.htm-corso36.htm) hanno
    # una sola <td> di primo livello che avvolge SIA il menu di navigazione
    # laterale SIA il contenuto reale (celle annidate senza margine, senza
    # class="testo" a distinguerle) -- prendere il <td> di primo livello
    # includerebbe anche il menu. Tra tutti i <td> (a qualunque profondità),
    # si sceglie il più piccolo/specifico che contiene comunque quasi tutto
    # il testo del candidato più ricco in assoluto: è la cella di contenuto
    # vera, non il suo wrapper.
    blocks = extract_class_blocks(body, require_class=None, tag_names=("td",), include_nested=True)
    if not blocks:
        return None
    lengths = [(b, _text_len(b)) for b in blocks]
    max_len = max(l for _, l in lengths)
    candidates = [b for b, l in lengths if l >= 0.9 * max_len]
    return min(candidates, key=len)


def _text_len(html_fragment: str) -> int:
    # spazi/a-capo collassati: una griglia di <img> decorativi senza alt (o
    # con alt corti) separati da molta indentazione/a-capo non deve contare
    # come "tanto testo" solo per lo spazio bianco tra i tag.
    text = re.sub(r"<[^>]+>", " ", html_fragment)
    return len(re.sub(r"\s+", " ", text).strip())


def _full_body_extraction(raw: str) -> str | None:
    """A differenza di _body_extraction (che sceglie UN <td> di contenuto),
    ritorna l'intero <body>: serve per le pagine con più <td> fratelli allo
    stesso livello che insieme formano il contenuto (es. corso/<N>/*.htm: un
    primo <td colspan> di intestazione/testo, poi righe di <td> con le foto
    della galleria) -- _body_extraction sceglierebbe solo il <td> con più
    testo (l'intestazione) e scarterebbe silenziosamente l'intera galleria."""
    m = re.search(r"<body[^>]*>(.*)</body>", raw, re.I | re.S)
    return m.group(1) if m else None


def extract_content(raw: str, mode: str) -> str:
    if mode == "full":
        result = _full_body_extraction(raw)
        if result is None:
            sys.exit("nessun <body> trovato per una pagina in modalità 'full'")
        return result
    if mode == "testo":
        result = _testo_extraction(raw)
        if result is None:
            sys.exit("nessuna cella class=testo trovata per una pagina in modalità 'testo'")
        return result
    if mode == "body":
        result = _body_extraction(raw)
        if result is None:
            sys.exit("nessun <td> trovato per una pagina in modalità 'body'")
        return result
    # mode == "auto": alcune pagine hanno UNA piccola cella class="testo"
    # incidentale (es. una didascalia sotto una foto) mentre il contenuto
    # vero sta in un <td> senza quella classe altrove nella stessa pagina
    # (verificato su corso25.htm-corso36.htm e alcune pagine eventi/: la
    # classificazione statica testo/body sbagliava silenziosamente su questi
    # casi, scegliendo la cella piccola) -- si estraggono entrambe e si
    # tiene quella con più testo reale.
    testo_result = _testo_extraction(raw)
    body_result = _body_extraction(raw)
    if testo_result is None and body_result is None:
        sys.exit("né una cella class=testo né un <td> di contenuto trovati (modalità 'auto')")
    if testo_result is None:
        return body_result
    if body_result is None:
        return testo_result
    return testo_result if _text_len(testo_result) >= _text_len(body_result) else body_result


def normalize_href(source_rel: str, href: str) -> str:
    """href trovato in source_rel (percorso relativo a OLD_ROOT) -> percorso
    normalizzato relativo a OLD_ROOT (per confronto con LINK_REWRITE/copia asset)."""
    base_dir = Path(source_rel).parent
    joined = (base_dir / href).as_posix()
    parts = []
    for part in joined.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    return "/".join(parts)


# Link esterni (fuori dal vecchio dominio del sito) il cui percorso profondo
# non esiste più, verificato via HTTP il 2026-08-12: il dominio stesso è
# ancora attivo, quindi si riscrive verso la sua radice invece di lasciare un
# link rotto o di indovinare un percorso sostitutivo specifico.
EXTERNAL_LINK_REWRITE = {
    # SSI ha unificato ssi.speleo.it sotto www.speleo.it.
    "http://www.ssi.speleo.it/": "https://www.speleo.it/",
    "http://www.ssi.speleo.it": "https://www.speleo.it/",
    "http://www.ssi.speleo.it/index.html": "https://www.speleo.it/",
    "http://www.ssi.speleo.it/it/eventi/gns2005.htm": "https://www.speleo.it/",
    "http://www.ssi.speleo.it/it/download/speleoteca.pdf": "https://www.speleo.it/",
    "http://www.ssi.speleo.it/it/cids.htm": "https://www.speleo.it/",
    "http://www.grottedicastellana.it/grotte-dintorni/index.htm": "https://www.grottedicastellana.it/",
    "http://www.grottedicastellana.it/it/eventi/70anniversario.htm": "https://www.grottedicastellana.it/",
    "http://www.grottediCastellana.it": "https://www.grottedicastellana.it/",
    "http://www.fscampania.it/alburni/corso/index.html": "http://www.fscampania.it/",
    "http://monopolilive.com/appuntamenti/appuntamento.aspx?idevent=513": "http://monopolilive.com/",
    "http://italia2tv.it/watch_video.php?v=944SR2D9WAW1": "http://italia2tv.it/",
    "http://www.promete.it/cainapoli/speleo.htm": "http://www.promete.it/",
    "http://www.comune.castellanagrotte.ba.it/2008/portale/index.php?special=changearea&newArea=101": "http://www.comune.castellanagrotte.ba.it/",
    "http://www.comune.castellanagrotte.ba.it/turismo/le-tradizioni-castellana-grotte.html": "http://www.comune.castellanagrotte.ba.it/",
}


def rewrite_links_and_images(html: str, source_rel: str, image_refs: set[str]) -> str:
    def href_repl(quote: str, href: str) -> str:
        if href.startswith("javascript:"):
            # javascript:MM_openBrWindow(...) -- popup verso una pagina old/
            # non migrata in questa fase (stessa policy di strip_popup_anchors,
            # per la forma alternativa href="javascript:..." invece di
            # href="#" onmouseup="...").
            return "data-stripped-href=" + quote + href + quote
        if href.startswith(("http://", "https://", "mailto:", "#")):
            if href.startswith("http://www.gruppopugliagrotte.it/") or href.startswith("https://www.gruppopugliagrotte.it/"):
                old_rel = href.split("gruppopugliagrotte.it/", 1)[1].split("?")[0].split("#")[0]
                if old_rel in LINK_REWRITE:
                    return f'href={quote}{LINK_REWRITE[old_rel]}{quote}'
                return "data-stripped-href=" + quote + href + quote
            if href in EXTERNAL_LINK_REWRITE:
                return f'href={quote}{EXTERNAL_LINK_REWRITE[href]}{quote}'
            return f'href={quote}{href}{quote}'
        norm = normalize_href(source_rel, href.split("?")[0].split("#")[0])
        if norm in LINK_REWRITE:
            return f'href={quote}{LINK_REWRITE[norm]}{quote}'
        # link interno a old/ non incluso in questa fase: si spoglia il link
        # (il testo resta, nessun href rotto)
        return "data-stripped-href=" + quote + href + quote

    # href="..." può contenere apici singoli al suo interno (tipico di
    # javascript:MM_openBrWindow('pagina.htm',...)) quando il delimitatore è
    # il doppio apice, e viceversa: la classe esclusa deve essere solo il
    # delimitatore usato, non entrambi.
    html = re.sub(r'href="([^"]*)"', lambda m: href_repl('"', m.group(1)), html, flags=re.I)
    html = re.sub(r"href='([^']*)'", lambda m: href_repl("'", m.group(1)), html, flags=re.I)

    def src_repl(m):
        quote, src = m.group(1), m.group(2)
        norm = IMAGE_SRC_OVERRIDES.get((source_rel, src)) or normalize_href(source_rel, src)
        image_refs.add(norm)
        return f'src={quote}/archivio-storico/legacy/{norm}{quote}'

    html = re.sub(r'src=("|\')([^"\']+\.(?:jpg|jpeg|gif|png))\1', src_repl, html, flags=re.I)
    return html


def strip_dead_anchors(html: str) -> str:
    """Rimuove i tag <a ...data-stripped-href=...>...</a> lasciando il testo
    interno (link verso pagine old/ non incluse in questa fase)."""
    return re.sub(
        r'<a\b[^>]*\bdata-stripped-href=(?:"[^"]*"|\'[^\']*\')[^>]*>(.*?)</a>',
        r"\1", html, flags=re.I | re.S,
    )


MM_POPUP_OPEN_TAG = re.compile(
    r'''<a\b(?=[^>]*\bhref=(["'])#\1)[^>]*\bonMouseUp=(["'])MM_openBrWindow\(\s*['"]([^'"]+)['"][^>]*>''',
    re.I,
)


def resolve_mm_popups(html: str, source_rel: str) -> str:
    """<a href="#" onMouseUp="MM_openBrWindow('target.htm',...)"> è come il
    sito apriva in popup una pagina old/ senza un href reale. Se quella pagina
    è nel frattempo stata migrata (presente in LINK_REWRITE, es. una nuova
    voce di PAGES/EVENTI_FILES/CORSI_FILES), si riscrive l'anchor con un href
    vero PRIMA che rewrite_links_and_images/strip_popup_anchors la tolgano
    come popup non migrato -- altrimenti resta intatta per loro (nessun
    effetto se il target non è ancora stato migrato)."""
    def repl(m):
        target = m.group(3)
        norm = normalize_href(source_rel, target.split("?")[0].split("#")[0])
        if norm not in LINK_REWRITE:
            return m.group(0)
        return f'<a href="{target}">'
    return MM_POPUP_OPEN_TAG.sub(repl, html)


BARE_HASH_ANCHOR = re.compile(
    r'''<a\b(?=[^>]*\bhref=(["'])#\1)[^>]*>(.*?)</a>''',
    re.I | re.S,
)


def strip_popup_anchors(html: str) -> str:
    """<a href="#" ...>...</a> con href="#" nudo (nessun nome di fragment) non
    è mai un'ancora reale in questo sito: o è un pseudo-link JS verso una
    pagina old/ non migrata in questa fase (onMouseUp="MM_openBrWindow(...)",
    es. foto singole, schede relatori), o è un placeholder rimasto tale anche
    sul sito originale (es. attivi/programma0607.htm: "Campo Braca"), o è
    un'utility JS senza vera destinazione (stampa/chiudi finestra). In tutti
    i casi va spogliato come gli altri link interni non inclusi, non lasciato
    come link morto."""
    return BARE_HASH_ANCHOR.sub(r"\2", html)


def html_to_md(html: str) -> str:
    # Passate di pulizia generiche, applicate a QUALUNQUE pagina passi da qui
    # (PAGES, bollettini, corsi, museo...): sicure ovunque perché toccano solo
    # spazzatura pre-CSS (attributi) o markup già rotto (anchor svuotati),
    # mai contenuto o struttura reale. Vedi i docstring delle singole funzioni.
    html = strip_legacy_presentational_attrs(html)
    html = unwrap_align_divs(html)
    html = fix_empty_backtotop_anchors(html)
    r = subprocess.run(
        ["pandoc", "-f", "html", "-t", "gfm", "--wrap=preserve"],
        input=html, capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(f"Errore pandoc: {r.stderr}")
    return r.stdout.strip()


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_index():
    safe_write_text(
        CONTENT / "_index.md",
        "\n".join([
            "---",
            'title: "Archivio storico"',
            'description: "Pagine recuperate dal sito del Gruppo Puglia Grotte precedente a WordPress (in linea 1999–2014)."',
            "---",
            "",
            "Questa sezione raccoglie pagine del sito precedente a WordPress "
            "(in linea indicativamente dal 1999 al 2014), recuperate dalla copia "
            "statica originale. Sono qui solo le pagine già citate da link reali "
            "nel resto del sito attuale — non è ancora un archivio completo del "
            "vecchio sito.",
            "",
            "**Le informazioni istituzionali qui contenute (composizione del "
            "Consiglio Direttivo, testo dello statuto, recapiti) sono storiche e "
            "superate**: per i dati aggiornati vedi [Chi siamo](/chi-siamo/).",
            "",
        ]) + "\n",
    )


def process_page(page: dict, image_refs: set[str], date: str | None = None):
    bodies = []
    for src in page["sources"]:
        path = OLD_ROOT / src
        raw = path.read_text(encoding="iso-8859-1")
        if src in SOURCE_PATCHES:
            find, repl = SOURCE_PATCHES[src]
            if find not in raw:
                sys.exit(f"SOURCE_PATCHES[{src}]: testo da sostituire non trovato (sorgente cambiato?)")
            raw = raw.replace(find, repl)
        content = extract_content(raw, page["mode"])
        content = strip_html_comments(content)
        content = strip_nav_icons(content)
        content = strip_print_close_widget(content)
        content = unwrap_absolute_divs(content)
        content = resolve_mm_popups(content, src)
        content = rewrite_links_and_images(content, src, image_refs)
        content = strip_dead_anchors(content)
        content = strip_popup_anchors(content)
        bodies.append(content)
    html = "\n<hr>\n".join(bodies)
    md = html_to_md(html)

    fm = ["---", f"title: {yaml_str(page['title'])}"]
    if date:
        # Vedi bugfix "01.01.0001": ogni pagina resa tramite layouts/_default/list.html
        # (post-card) mostra la data del front matter; qui non esiste un dato
        # reale (queste pagine non hanno mai avuto un "post_date" nel senso
        # WordPress), quindi si usa la stessa data convenzionale della
        # rimigrazione adottata per tutte le altre pagine senza data reale.
        fm.append(f"date: {date}")
    fm.append('description: "Pagina storica, recuperata dal sito del Gruppo Puglia Grotte precedente a WordPress."')
    fm.append("---")
    fm.append("")
    dest = CONTENT / f"{page['slug']}.md"
    safe_write_text(dest, "\n".join(fm) + md + "\n")


def find_case_insensitive(path: Path) -> Path | None:
    """old/ girava su un server Windows (case-insensitive); alcuni href nel
    sorgente usano una capitalizzazione diversa da quella reale su disco
    (es. "images/cnr.jpg" per il vero "images/CNR.jpg")."""
    if not path.parent.is_dir():
        return None
    target = path.name.lower()
    for candidate in path.parent.iterdir():
        if candidate.name.lower() == target:
            return candidate
    return None


def copy_assets(image_refs: set[str], direct_assets: set[str] = frozenset(DIRECT_ASSETS)):
    all_refs = set(direct_assets) | image_refs
    copied, missing = 0, []
    for rel in sorted(all_refs):
        src = OLD_ROOT / rel
        dst = STATIC_LEGACY / rel
        if not src.exists():
            fallback = find_case_insensitive(src)
            if fallback is None:
                missing.append(rel)
                continue
            src = fallback
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    print(f"copiati {copied} file in {STATIC_LEGACY.relative_to(REPO)}/")
    for f in missing:
        warnings.append(f"asset referenziato ma non trovato in old/: {f}")


def main():
    write_index()
    image_refs: set[str] = set()
    for page in PAGES:
        process_page(page, image_refs)
    copy_assets(image_refs)
    apply_post_fixups()
    save_manifest()
    export_link_rewrite()

    if warnings:
        print("\n== Avvisi ==")
        for w in warnings:
            print(f"- {w}")


# =============================================================================
# Fase 2 (parziale): "Cronaca eventi" 2003-2014 e "Corsi" 1-36, come sotto-
# sezioni di archivio-storico/ (archivio-storico/eventi/, archivio-storico/corsi/).
# Non tocca nessuna delle pagine già scritte da main() sopra (Fase 1): PAGES,
# write_index() e i loro asset restano invariati. Le pagine sono qui elencate
# come dati (nome file -> modalità di estrazione, verificata pagina per pagina
# in sessione con extract_class_blocks) anziché scritte a mano come in PAGES,
# vista la quantità (69 + 19 pagine): un errore di modalità qui fa fallire
# rumorosamente extract_content, non produce contenuto silenziosamente vuoto.
# =============================================================================

DATE_RIMIGRAZIONE = "2026-08-01"

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    return SLUG_RE.sub("-", name.lower()).strip("-")


TITLE_SECTION_LABELS = {"Eventi", "Didattica", "Esplorazione e ricerca", "Pubblicazioni"}


def derive_title(raw: str) -> str:
    import html
    m = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
    title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else "?"
    # Formato costante nel sito: "Gruppo Puglia Grotte - [Eventi - ]Titolo vero",
    # ma il titolo vero può contenere a sua volta un " - " (es. "Un falò per il
    # Mozambico - Edizione 2010"): NON si può prendere solo l'ultimo segmento
    # (rsplit), va tolto solo il prefisso fisso (nome sito + eventuale sezione).
    parts = title.split(" - ")
    if parts and parts[0].strip() == "Gruppo Puglia Grotte":
        parts = parts[1:]
    if parts and parts[0].strip() in TITLE_SECTION_LABELS:
        parts = parts[1:]
    return " - ".join(parts).strip() or title


# eventi/*.htm inclusi (esclusi: _eng.htm, pagine di puro redirect/chrome
# come index1024.htm, le 3 pagine già migrate in Fase 1 -- convegno2007.htm,
# spelaion2011.htm, speleonight.htm --, le sotto-pagine popup senza voce
# propria nel sito -- Arrivedpresid.htm, cuba2006.{imm,inv,rel}.htm,
# falo2005_{2,3,4,5}.htm, speleofilm2011_2.htm --, e rass_ita.htm che è
# l'indice della rassegna stampa: ~180 ritagli scannerizzati in rassegna/,
# fuori scope, eventuale archivio a sé in futuro).
EVENTI_FILES = {
    "40anni.htm": "auto", "acqua.htm": "auto", "ambienteitalia.htm": "auto",
    "anniversario04.htm": "auto", "anniversario08.htm": "auto", "anniversario09.htm": "auto",
    "anniversario10.htm": "auto", "anniversario11.htm": "auto", "anniversario12.htm": "auto",
    "anniversario13.htm": "auto", "anniversario14.htm": "auto", "bacca.htm": "auto",
    "catasto.htm": "auto", "consigliossi.htm": "auto", "convegnocampania2010.htm": "auto",
    "corsoarmo2013.htm": "auto", "corsoarmo.htm": "auto", "cuba2006.htm": "auto",
    "EsamiAIIT2013.htm": "auto", "falo2004.htm": "auto", "falo2005.htm": "auto",
    "falo2006.htm": "auto", "falo2007.htm": "auto", "falo2008.htm": "auto",
    "falo2009.htm": "auto", "falo2010.htm": "auto", "falo2011.htm": "auto",
    "falo2012.htm": "auto", "falo2013.htm": "auto", "festafaiano.htm": "auto",
    "fuoridigusto.htm": "auto", "gemellaggio.htm": "auto", "gigi.htm": "auto",
    "giornazionale2003.htm": "auto", "giornazionale.htm": "auto", "gns2005.htm": "auto",
    "golgota.htm": "auto", "gravinelle2006.bis.htm": "auto", "gravinelle2006.htm": "auto",
    "gravinelle.htm": "auto", "Martino.htm": "auto", "mediterre.htm": "auto",
    "meuli.htm": "auto", "newpresidentegae.htm": "auto", "nuovegrotte.htm": "auto",
    "ora.htm": "auto", "perama.htm": "auto", "pianetam.htm": "auto",
    "pib2006.htm": "auto", "pib2007.htm": "auto", "pib2008.htm": "auto",
    "pib2009.htm": "auto", "pib2010.htm": "auto", "pib2011.htm": "auto",
    "pib2012.htm": "auto", "pib2013.htm": "auto", "presidente.htm": "auto",
    "presidentenew.htm": "auto", "scarburo2006.htm": "auto", "sereno.htm": "auto",
    "sideout2011.htm": "auto", "Solaris.htm": "auto", "spelaion2004.htm": "auto",
    "speleofilm2011.htm": "auto", "stage.htm": "auto", "ticiportoio.htm": "auto",
    "unomattina.htm": "auto", "vivicastellana.htm": "auto",
}

# corso*.htm inclusi: solo le edizioni numerate 18-36 (root: corso18-25.htm,
# poi corso/corso26-36.htm). corso.htm/corso2-4.htm ESCLUSI: nonostante il
# nome, non sono edizioni del corso ma una serie di gallerie fotografiche
# ("Le immagini - Gruppo in grotta/Palestra di roccia...") -- numerazione
# coincidente ma argomento diverso, verificato dal <title>. Edizioni 1 e 5-17
# non hanno una pagina propria in old/ (probabilmente mai realizzate: il sito
# stesso salta da corso4.htm, che è tutt'altro, a corso18.htm).
CORSI_FILES = {
    "corso18.htm": "auto", "corso19.htm": "auto", "corso20.htm": "auto",
    "corso21.htm": "auto", "corso22.htm": "auto", "corso23.htm": "auto",
    "corso24.htm": "auto", "corso25.htm": "auto",
    "corso/corso26.htm": "auto", "corso/corso27.htm": "auto", "corso/corso28.htm": "auto",
    "corso/corso29.htm": "auto", "corso/corso30.htm": "auto", "corso/corso31.htm": "auto",
    "corso/corso32.htm": "auto", "corso/corso33.htm": "auto", "corso/corso34.htm": "auto",
    "corso/corso35.htm": "auto", "corso/corso36.htm": "auto",
}

# (src_rel) -> titolo corretto, per refusi genuini nel <title> del sorgente
# (non invenzione: solo correzione di un errore di battitura verificabile).
TITLE_OVERRIDES = {
    # "Il XIIIV Corso di Speleologia" nel sorgente 1996 -- numerazione romana
    # non valida, refuso per "XVIII" (18°), coerente con la sequenza reale
    # delle edizioni (corso19.htm = XIX, corso20.htm = XX, ...).
    "corso18.htm": "Il XVIII Corso di Speleologia",
    # corso23-25.htm usano nel sorgente la numerazione decimale ("23°", "24°",
    # "25°") invece del numero romano usato da tutte le altre edizioni
    # (corso18-22.htm, corso26-36.htm): normalizzate per coerenza nella
    # sezione, stesso numero d'edizione, solo la notazione cambia.
    "corso23.htm": "Il XXIII Corso di Speleologia",
    "corso24.htm": "Il XXIV Corso di Speleologia",
    "corso25.htm": "Il XXV Corso di Speleologia",
}


def build_pages(files: dict[str, str], src_dir: str, dest_prefix: str) -> list[dict]:
    pages = []
    seen_slugs: set[str] = set()
    for fname, mode in files.items():
        src_rel = fname if "/" in fname else f"{src_dir}/{fname}" if src_dir else fname
        raw = (OLD_ROOT / src_rel).read_text(encoding="iso-8859-1")
        title = TITLE_OVERRIDES.get(fname, derive_title(raw))
        slug = slugify(Path(fname).stem)
        if slug in seen_slugs:
            sys.exit(f"slug duplicato per {src_rel}: {slug}")
        seen_slugs.add(slug)
        pages.append({
            "slug": f"{dest_prefix}/{slug}",
            "title": title,
            "sources": [src_rel],
            "mode": mode,
        })
        LINK_REWRITE[src_rel] = f"/archivio-storico/{dest_prefix}/{slug}/"
    return pages


def write_subsection_index(dest_prefix: str, title: str, intro: str):
    dest = CONTENT / dest_prefix / "_index.md"
    safe_write_text(
        dest,
        "\n".join([
            "---",
            f"title: {yaml_str(title)}",
            f"date: {DATE_RIMIGRAZIONE}",
            f"description: {yaml_str(intro)}",
            "---",
            "",
            intro,
            "",
        ]) + "\n",
    )


def extend_archive():
    """Fase 2 (parziale): non chiama main() né riscrive nessuna delle pagine
    di Fase 1 -- solo le nuove sotto-sezioni eventi/ e corsi/."""
    eventi_pages = build_pages(EVENTI_FILES, "eventi", "eventi")
    corsi_pages = build_pages(CORSI_FILES, "", "corsi")

    write_subsection_index(
        "eventi",
        "Cronaca eventi (2003–2014)",
        "Cronaca degli eventi organizzati o cui ha partecipato il Gruppo Puglia "
        "Grotte tra il 2003 e il 2014, recuperata dal sito precedente a "
        "WordPress: falò benefici, anniversari della scoperta delle Grotte di "
        "Castellana, Puliamo il Buio, apparizioni televisive e altri eventi "
        "pubblici. Non ancora la cronaca completa del vecchio sito.",
    )
    write_subsection_index(
        "corsi",
        "Corsi di speleologia, edizioni storiche (XVIII–XXXVI)",
        "Edizioni storiche del corso di speleologia di primo livello, dalla "
        "XVIII alla XXXVI, recuperate dal sito precedente a WordPress. Le "
        "edizioni successive (dalla 37ª) sono nella sezione [Corsi](/corsi/) "
        "corrente.",
    )

    image_refs: set[str] = set()
    for page in eventi_pages + corsi_pages:
        process_page(page, image_refs, date=DATE_RIMIGRAZIONE)
    copy_assets(image_refs, direct_assets=set())
    save_manifest()
    export_link_rewrite()

    if warnings:
        print("\n== Avvisi ==")
        for w in warnings:
            print(f"- {w}")


# =============================================================================
# Fase 3: indici dei "Bollettini Puglia Grotte", annata per annata. Tutte le
# 11 annate (comprese 1984/1985, inizialmente migrate a mano da pagine
# WordPress reali con una formattazione leggermente diversa -- font/colore
# inline superstite dall'editor WP, intestazione "Indice" incoerente con le
# altre) vengono qui rigenerate dalla STESSA fonte (pagina radice <anno>.htm
# in old/, verificata identica nei contenuti alla versione WP) per uniformità
# di formato. 1984/1985 sono le uniche due che avevano un permalink WordPress
# reale: mantengono il loro alias di redirect, le altre 9 non ne hanno mai
# avuto uno.
# =============================================================================

BOLLETTINI_CONTENT = REPO / "content" / "pubblicazioni" / "bollettini-puglia-grotte"

# anno -> file radice in old/.
BOLLETTINI_FILES = {
    1984: "1984.htm", 1985: "1985.htm", 1986: "1986.htm", 1991: "1991.htm",
    1993: "1993.htm", 1995: "1995.htm", 1996: "1996.htm", 1999: "1999.htm",
    2001: "2001.htm", 2003: "2003.htm", 2008: "2008.htm",
}

# anno -> (larghezza, altezza) reali della copertina scansionata (non tutte
# identiche: le annate 1995/1996 sono leggermente più strette, il 2008 più
# alto). Default 96x136 se un anno non è qui.
BOLLETTINI_DIMS = {1995: (97, 135), 1996: (97, 135), 2008: (96, 138)}

# anno -> alias di redirect, solo per le due annate che hanno davvero avuto
# un permalink WordPress prima di questo script.
BOLLETTINI_ALIASES = {
    1984: "/home/pubblicazioni/bollettini-puglia-grotte/bollettino-1984/",
    1985: "/home/pubblicazioni/bollettini-puglia-grotte/bollettino-1985/",
}

# Il link di download del bollettino 2008 in pdf (le altre annate non hanno
# un pdf scaricabile in old/, solo l'indice testuale).
LINK_REWRITE["bollettini/2008/GPGBollettino2008.pdf"] = \
    "/archivio-storico/legacy/bollettini/2008/GPGBollettino2008.pdf"

# Ogni <anno>.htm apre con lo stesso blocco fisso (link "torna alla home" +
# copertina + intestazione "Puglia Grotte - <anno>"), ridondante qui perché
# la pagina Hugo ha già titolo e una propria <figure> di copertina: si toglie
# tutto fino a questa intestazione compresa, lasciando "Indice"/il link di
# download e la lista degli articoli.
BOLLETTINO_HEADER_RE = re.compile(
    r"^.*?<b>Puglia Grotte - \d{4}</b>\s*(?:<br\s*/?>\s*)*",
    re.I | re.S,
)


def build_bollettini():
    """Idempotente come main()/extend_archive(): sovrascrive sempre le 11
    pagine bollettino-<anno>.md con la stessa fonte/formattazione."""
    BOLLETTINI_CONTENT.mkdir(parents=True, exist_ok=True)
    image_refs: set[str] = set()
    for year, fname in BOLLETTINI_FILES.items():
        dest = BOLLETTINI_CONTENT / f"bollettino-{year}.md"
        raw = (OLD_ROOT / fname).read_text(encoding="iso-8859-1")
        content = extract_content(raw, "body")
        content = strip_html_comments(content)
        content = strip_nav_icons(content)
        content = strip_print_close_widget(content)
        content, n = BOLLETTINO_HEADER_RE.subn("", content, count=1)
        if n == 0:
            sys.exit(f"{fname}: intestazione 'Puglia Grotte - {year}' non trovata (sorgente cambiato?)")
        content = resolve_mm_popups(content, fname)
        content = rewrite_links_and_images(content, fname, image_refs)
        content = strip_dead_anchors(content)
        content = strip_popup_anchors(content)
        md = html_to_md(content)

        w, h = BOLLETTINI_DIMS.get(year, (96, 136))
        cover = f"/archivio-storico/legacy/images/{year}_little.jpg"
        fm = [
            "---",
            f"title: {yaml_str(f'Bollettino {year}')}",
            f"date: {DATE_RIMIGRAZIONE}",
        ]
        if year in BOLLETTINI_ALIASES:
            fm.append("aliases:")
            fm.append(f"  - {yaml_str(BOLLETTINI_ALIASES[year])}")
        fm += [
            "---",
            "",
            "<figure>",
            f'<img src="{cover}" title="Copertina" style="margin: 0px 5px; border: 1px solid black;" data-align="right" data-border="1" data-hspace="5" data-vspace="0" width="{w}" height="{h}" alt="Copertina" />',
            f"<figcaption>Bollettino {year}</figcaption>",
            "</figure>",
            "",
            # riga vuota indispensabile: senza uno stacco netto dal blocco
            # HTML <figure> precedente, goldmark tratta quello che segue
            # (l'intestazione "**Indice**") come continuazione dello stesso
            # blocco HTML grezzo e non lo interpreta come Markdown (verificato
            # sul rendering: **Indice** restava testo letterale non in
            # grassetto, mentre l'elenco più sotto veniva comunque riconosciuto
            # perché <ol> avvia un nuovo blocco HTML riconosciuto a sé).
            "",
        ]
        safe_write_text(dest, "\n".join(fm) + md + "\n")

    copy_assets(image_refs, direct_assets={"bollettini/2008/GPGBollettino2008.pdf"})
    save_manifest()
    export_link_rewrite()
    if warnings:
        print("\n== Avvisi ==")
        for w in warnings:
            print(f"- {w}")


# =============================================================================
# Fase 4: testo integrale degli articoli dei bollettini (bollettini/*.htm),
# oltre al solo indice già presente in bollettino-<anno>.md (Fase 3). Una
# pagina content/archivio-storico/bollettini/<anno>/<slug>.md per articolo.
#
# Nota encoding: a differenza del resto di old/ (decodificato "iso-8859-1" nel
# resto di questo script, verificato con `file`), i sorgenti di bollettini/
# contengono byte 0x80-0x9F genuinamente Windows-1252 (es. l'apostrofo curvo
# 0x92 in "L\x92Aviso" -> "L'Aviso" in dellerose_2001.htm) che iso-8859-1
# decodificherebbe come caratteri di controllo/lettere accentate sbagliate
# (es. 0x92 -> "\x92" non stampabile, la "Á" di scarto vista in un test
# preliminare veniva dal byte successivo). "cp1252" decodifica quei byte
# correttamente ed è identico a iso-8859-1 su tutto il resto (0x00-0x7F e
# 0xA0-0xFF): nessuna regressione possibile sulle fasi precedenti, che restano
# su iso-8859-1 e non vengono toccate da questa funzione.
# =============================================================================

BOLLETTINI_TESTO_DIR = OLD_ROOT / "bollettini"
BOLLETTINI_TESTO_CONTENT = REPO / "content" / "archivio-storico" / "bollettini"

# anno esplicito per gli articoli che non sono del 2001 (la cartella radice di
# bollettini/ mescola annate diverse, verificato confrontando ogni <title> con
# l'indice reale in content/pubblicazioni/bollettini-puglia-grotte/
# bollettino-<anno>.md); bollettini/2003/ invece è tutta il 2003.
_BOLLETTINI_TESTO_YEAR_OVERRIDES = {
    "SpeleoFlash_1991.htm": 1991, "comparelliManghisi_1991.htm": 1991,
    "comparelli_1986.htm": 1986,
    "lovece1996.htm": 1996,
    "lovece1999.htm": 1999, "quinto1999.htm": 1999,
}

# 2003/didonna_esp.htm non ha una voce propria nell'indice: è la versione
# spagnola dello stesso articolo di 2003/didonna.htm (bollettino-2003.md,
# voce 6: "Corsi di Speleologia in Costarica" / "Cursos de Espeleología en
# Costa Rica (en español)", un solo item, due lingue) -- una sola pagina Hugo
# con entrambe, non due pagine separate.
_BOLLETTINI_TESTO_MERGE_SOURCES = {
    "2003/didonna.htm": ["2003/didonna_esp.htm"],
}
_BOLLETTINI_TESTO_MERGED_AWAY = {
    src for srcs in _BOLLETTINI_TESTO_MERGE_SOURCES.values() for src in srcs
}

# titolo reale (dal corpo della pagina) per i pochi file il cui <title> è
# sbagliato nel sorgente stesso (refuso di copia-incolla, non invenzione):
# speleoflash_2001.htm ha <title>...Proyecto Cuatrocienegas...</title>,
# identico per errore al file bernabei_2001.htm adiacente, mentre il proprio
# <b> in pagina dice "Speleo flash" (coerente con bollettino-2001.md, voce 28).
BOLLETTINI_TESTO_TITLE_OVERRIDES = {
    "speleoflash_2001.htm": "Speleo flash",
}


def _discover_bollettini_testo() -> dict[str, int]:
    files: dict[str, int] = {}
    for p in sorted(BOLLETTINI_TESTO_DIR.glob("*.htm")):
        files[p.name] = _BOLLETTINI_TESTO_YEAR_OVERRIDES.get(p.name, 2001)
    for p in sorted((BOLLETTINI_TESTO_DIR / "2003").glob("*.htm")):
        files[f"2003/{p.name}"] = 2003
    for merged in _BOLLETTINI_TESTO_MERGED_AWAY:
        del files[merged]
    return files


# dellerose_2001.htm ha una corruzione genuina del sorgente (non un problema
# di decodifica): l'apostrofo curvo 0x92 di "l'Aviso"/"dell'aviso" è seguito
# da un byte accentato estraneo (0xC0 "À" o 0xE0 "à") invece della lettera
# "A"/"a" attesa -- 14 occorrenze verificate, sempre e solo in questo file,
# sempre subito prima di "viso". Corretto qui, sui byte grezzi, prima della
# decodifica (stesso principio di SOURCE_PATCHES sopra: fix di un refuso
# genuino del sorgente, non contenuto alterato).
BOLLETTINI_TESTO_BYTE_PATCHES = {
    "dellerose_2001.htm": [
        (b"\x92\xc0viso", b"\x92Aviso"),
        (b"\x92\xe0viso", b"\x92aviso"),
    ],
}


def _read_bollettino_source(rel: str) -> str:
    path = BOLLETTINI_TESTO_DIR / rel
    raw = path.read_bytes()
    for find, repl in BOLLETTINI_TESTO_BYTE_PATCHES.get(rel, []):
        if find not in raw:
            sys.exit(f"BOLLETTINI_TESTO_BYTE_PATCHES[{rel}]: pattern non trovato (sorgente cambiato?)")
        raw = raw.replace(find, repl)
    return raw.decode("cp1252")


BOLLETTINO_ARTICLE_TITLE_TAG_RE = re.compile(
    r"<title>Gruppo Puglia Grotte - Pubblicazioni - Puglia Grotte - \d{4} - (.*?)</title>",
    re.S,
)


def derive_bollettino_title(fname: str, raw: str) -> str:
    if fname in BOLLETTINI_TESTO_TITLE_OVERRIDES:
        return BOLLETTINI_TESTO_TITLE_OVERRIDES[fname]
    m = BOLLETTINO_ARTICLE_TITLE_TAG_RE.search(raw)
    if not m:
        sys.exit(f"{fname}: <title> non nel formato atteso 'Puglia Grotte - YYYY - Titolo'")
    import html as _html
    return _html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()


# indice cliccabile (<ul>/<ol> con voci che linkano ad ancore #N più sotto
# nella stessa pagina), presente solo negli articoli più lunghi -- ridondante
# su una singola pagina Hugo senza paginazione. Tolto solo se OGNI link della
# lista punta a un'ancora (#...), per non toccare mai un elenco che sia
# contenuto reale (es. l'elenco soci di members_2001.htm/2003/x.htm, che non
# ha alcun href).
NAV_TOC_LIST_RE = re.compile(r"<(ul|ol)\b[^>]*>(.*?)</\1>", re.I | re.S)


def strip_anchor_toc(html: str) -> str:
    def repl(m):
        block = m.group(0)
        hrefs = re.findall(r'href=(["\'])(.*?)\1', block, re.I)
        if hrefs and all(h.startswith("#") for _, h in hrefs):
            return ""
        return block
    return NAV_TOC_LIST_RE.sub(repl, html)


ANCHOR_NAME_RE = re.compile(r'<a\s+name="[^"]*"\s*></a>', re.I)
# "<div align=right><a href=#top><b>^^^</b></a></div>" ("Torna in alto") o la
# variante "<div align=right><a href=#up title="Torna su"><b>^ Torna su
# ^</b></a></div>" -- stesso widget di rimando all'inizio pagina, due href
# d'ancora diversi usati a seconda del file. Riconosciuto dal testo (un
# accento circonflesso "^"), non da un href fisso, per coprire entrambe le
# forme senza un'unione manuale di alternative fragile.
BACK_TO_TOP_RE = re.compile(
    r'(<br\s*/?>\s*)*<div[^>]*align="right"[^>]*>\s*(?:<a\b[^>]*href="#(?:top|up)"[^>]*>\s*)?<b>[^<]*\^[^<]*</b>\s*(?:</a>\s*)?</div>',
    re.I | re.S,
)
# footer di chiusura ripetuto identico su ogni pagina di bollettini/ ("<div
# align=center><font...><a onMouseUp="MM_openBrWindow('...copy.htm',...)">©
# Gruppo Puglia Grotte</a></font></div>"): puro chrome del popup "note legali"
# del sito originale, non contenuto dell'articolo -- rimosso per intero
# (non solo il link, come farebbe strip_popup_anchors) invece di degradare a
# testo semplice "© Gruppo Puglia Grotte" in coda a ogni pagina.
COPYRIGHT_FOOTER_RE = re.compile(
    r'<div[^>]*align="center"[^>]*>\s*<font[^>]*>\s*<a\b[^>]*copy\.htm[^>]*>.*?</a>\s*</font>\s*</div>',
    re.I | re.S,
)


def strip_bollettino_chrome(html: str) -> str:
    html = ANCHOR_NAME_RE.sub("", html)
    html = BACK_TO_TOP_RE.sub("", html)
    html = COPYRIGHT_FOOTER_RE.sub("", html)
    return html


# <div align="right|center|left"> è usato in bollettini/ sia per chrome di
# navigazione (già tolto sopra) sia per contenuto reale (un'immagine centrata,
# un paragrafo di chiusura allineato a destra, es. "Buona lettura!" in
# 2003/sgobba.htm): pandoc non sa esprimere l'allineamento in Markdown e
# lascia l'intero <div> come HTML grezzo nell'output. Tolto qui solo il
# wrapper (non il contenuto, a differenza delle funzioni di chrome sopra) --
# l'allineamento stesso non ha equivalente Markdown e si perde, come già
# accade altrove nel sito per lo stesso motivo (unwrap_absolute_divs).
ALIGN_DIV_RE = re.compile(r'<div[^>]*\balign="(?:right|center|left)"[^>]*>(.*?)</div>', re.I | re.S)


def unwrap_align_divs(html: str) -> str:
    prev = None
    while prev != html:
        prev = html
        html = ALIGN_DIV_RE.sub(r"\1", html)
    return html


# strip_nav_icons toglie solo l'<img> (vedi il suo docstring: alcune icone
# stanno dentro <a href="#N"> di navigazione reale che deve restare
# funzionante). Quando quell'<img> era l'UNICO contenuto dell'<a> -- caso
# tipico delle icone upbianco.gif/on.gif/top.gif usate come link "torna
# su"/indice puramente iconografici, senza testo alternativo accanto --
# l'anchor resta vuoto e pandoc lo rende come "[](#up "...")": un link privo
# di testo visibile, invisibile ma comunque cliccabile, che sul sito
# originale invece si vedeva (era l'icona). Stesso sintomo anche per un bug
# distinto di BACK_TO_TOP_RE (sotto): quando il markup sorgente ha l'ordine
# invertito rispetto a quanto la regex si aspetta ("<a href=#up><div
# align=right><b>^ Torna su ^</b></div></a>" invece di "<div><a><b>...）,
# la regex toglie comunque il "<div>...</div>" interno ma non l'<a> che lo
# racchiudeva, lasciando lo stesso <a href="#up"></a> vuoto. Riconosciuto qui
# per href (non per come si è svuotato) e sostituito con lo stesso testo
# "^ Torna su ^" già usato per il widget quando il markup è integro altrove
# nel sito -- non un'invenzione, la stessa dicitura del sito originale.
EMPTY_BACKTOTOP_ANCHOR_RE = re.compile(
    r'<a\b[^>]*\bhref="(#(?:up|top))"[^>]*>\s*</a>', re.I,
)


def fix_empty_backtotop_anchors(html: str) -> str:
    def repl(m):
        return f'<a href="{m.group(1)}" title="Torna su"><b>^ Torna su ^</b></a>'
    return EMPTY_BACKTOTOP_ANCHOR_RE.sub(repl, html)


# Attributi HTML presentazionali pre-CSS (border/align/valign/bgcolor/
# cellspacing/cellpadding/bordercolor/hspace/vspace su img e tabelle):
# pandoc non ha un equivalente Markdown per loro e li porta comunque in
# output rinominandoli "data-*" (attributo HTML5 valido ma senza alcun
# effetto sul rendering, verificato: nessun CSS del tema li interpreta) --
# puro rumore nel sorgente Markdown, non contenuto. Tolti qui, PRIMA di
# pandoc, così l'output è pulito invece di portarsi dietro la spazzatura
# "data-*". width/height su <img> sono tenuti (dimensioni reali, non
# presentazione) così come style="width:NN%" su <col> (unica forma con cui
# le tabelle a più colonne esprimono le proporzioni, non ha equivalente
# Markdown ma è informazione layout reale, non un residuo).
IMG_STRIP_ATTRS = frozenset({"border", "align", "hspace", "vspace"})
TABLE_STRIP_ATTRS = frozenset({
    "border", "align", "valign", "bgcolor", "cellspacing", "cellpadding",
    "bordercolor", "width",
})
TABLE_TAGS = frozenset({"table", "tr", "td", "th", "col", "colgroup", "caption", "tbody", "thead"})
TAG_OPEN_RE = re.compile(r'<(\w+)((?:\s+[\w-]+\s*=\s*"[^"]*")*)\s*(/?)>')
ATTR_RE = re.compile(r'\s+([\w-]+)\s*=\s*"[^"]*"')


def strip_legacy_presentational_attrs(html: str) -> str:
    def repl(m):
        tag, attrs_str, self_close = m.group(1), m.group(2), m.group(3)
        tag_lower = tag.lower()
        if tag_lower == "img":
            remove = IMG_STRIP_ATTRS
        elif tag_lower in TABLE_TAGS:
            remove = TABLE_STRIP_ATTRS
        else:
            return m.group(0)
        new_attrs = ATTR_RE.sub(
            lambda am: "" if am.group(1).lower() in remove else am.group(0),
            attrs_str,
        )
        return f"<{tag}{new_attrs}{self_close}>"
    return TAG_OPEN_RE.sub(repl, html)


# pandoc, di fronte a un <a> con QUALSIASI attributo oltre a href/title (es.
# target="_blank" -- comune nei link esterni di bollettini/), lo lascia HTML
# grezzo nel Markdown invece di convertirlo in [testo](url) (stesso problema
# già risolto per il contenuto WordPress in wp_to_hugo.py:simplify_tags,
# verificato anche qui su 2003/didonna.htm: <a href=... target="_blank"
# title=...> restava intatto in output). Applicato solo qui (non nel resto di
# questo script, che già produce Markdown pulito senza) per non toccare
# l'output già verificato delle Fasi 1-3.
BOLLETTINO_ANCHOR_TAG_RE = re.compile(r'<a\s+([^>]*)>', re.I)


def simplify_bollettino_anchors(html: str) -> str:
    def repl(m):
        found = dict(re.findall(r'([\w-]+)\s*=\s*"([^"]*)"', m.group(1)))
        if "href" not in found:
            keep = ("name", "id")
        else:
            keep = ("href", "title")
        attrs = " ".join(f'{k}="{found[k]}"' for k in keep if found.get(k))
        return f"<a {attrs}>"
    return BOLLETTINO_ANCHOR_TAG_RE.sub(repl, html)


def slugify_bollettino(fname: str) -> str:
    stem = Path(fname).stem
    return slugify(stem)


def process_bollettino_article(fname: str, year: int, image_refs: set[str]) -> tuple[str, str]:
    """Ritorna (slug, title). Scrive la pagina Hugo."""
    sources = [fname] + _BOLLETTINI_TESTO_MERGE_SOURCES.get(fname, [])
    raw0 = _read_bollettino_source(fname)
    title = derive_bollettino_title(fname, raw0)

    bodies = []
    for i, src in enumerate(sources):
        raw = _read_bollettino_source(src)
        content = extract_content(raw, "body")
        content = strip_html_comments(content)
        content = strip_nav_icons(content)
        content = strip_print_close_widget(content)
        content = strip_anchor_toc(content)
        content = strip_bollettino_chrome(content)
        content = unwrap_align_divs(content)
        content = unwrap_absolute_divs(content)
        content, n = BOLLETTINO_HEADER_RE.subn("", content, count=1)
        if n == 0:
            sys.exit(f"bollettini/{src}: intestazione 'Puglia Grotte - {year}' non trovata")
        src_rel = f"bollettini/{src}"
        content = resolve_mm_popups(content, src_rel)
        content = rewrite_links_and_images(content, src_rel, image_refs)
        content = strip_dead_anchors(content)
        content = strip_popup_anchors(content)
        content = simplify_bollettino_anchors(content)
        if i > 0:
            # seconda fonte unita (es. la versione spagnola di un articolo):
            # separatore esplicito, non fusione silenziosa dei due testi.
            content = "<p><b>Versión en español</b></p>\n" + content
        bodies.append(content)
    html = "\n<hr>\n".join(bodies)
    md = html_to_md(html)

    slug = slugify_bollettino(fname)
    fm = [
        "---",
        f"title: {yaml_str(title)}",
        f"date: {year}-11-16",
        'description: "Pagina storica, recuperata dal sito del Gruppo Puglia Grotte precedente a WordPress."',
        "---",
        "",
    ]
    dest = BOLLETTINI_TESTO_CONTENT / str(year) / f"{slug}.md"
    safe_write_text(dest, "\n".join(fm) + md + "\n")
    return slug, title


def write_bollettini_testo_index():
    safe_write_text(
        BOLLETTINI_TESTO_CONTENT / "_index.md",
        "\n".join([
            "---",
            'title: "Bollettini — testo integrale degli articoli"',
            f"date: {DATE_RIMIGRAZIONE}",
            'description: "Testo integrale degli articoli dei bollettini Puglia Grotte 1986-2003, recuperato dal sito precedente a WordPress."',
            "---",
            "",
            "Testo integrale dei singoli articoli dei bollettini, recuperato dal sito "
            "precedente a WordPress. Gli indici completi di ogni annata sono in "
            "[Bollettini Puglia Grotte](/pubblicazioni/bollettini-puglia-grotte/), "
            "che linka anche a queste pagine.",
            "",
        ]) + "\n",
    )


def build_bollettini_testo():
    write_bollettini_testo_index()
    files = _discover_bollettini_testo()
    image_refs: set[str] = set()
    generated: dict[str, tuple[int, str, str]] = {}  # fname -> (year, slug, title)
    for fname, year in files.items():
        slug, title = process_bollettino_article(fname, year, image_refs)
        generated[fname] = (year, slug, title)
    copy_assets(image_refs, direct_assets=set())
    save_manifest()

    print(f"\n{len(generated)} articoli generati sotto content/archivio-storico/bollettini/")
    if warnings:
        print("\n== Avvisi ==")
        for w in warnings:
            print(f"- {w}")
    return generated


# indice (bollettino-<anno>.md) -> testo esatto dello *titolo* corsivo da
# collegare, per i casi in cui il titolo derivato dall'articolo (Fase 4) non
# coincide carattere per carattere con quello scritto nell'indice (Fase 3,
# generato da un'altra pagina sorgente di old/, l'<anno>.htm radice): refusi
# indipendenti tra le due pagine originali (es. "una"/"un", virgola/trattino),
# maiuscole diverse (Speleo Flash/Speleo flash), o titoli su due righe nel
# markdown dell'indice di cui si collega solo la parte in corsivo. Verificato
# a mano confrontando ogni caso, non un'euristica automatica.
BOLLETTINI_INDEX_LINK_OVERRIDES = {
    "SpeleoFlash_1991.htm": "Speleo Flash",
    "lovece1999.htm": "Grande come la paura",
    "amatulli_2001.htm": "Alburni: ancora nuove scoperte, Metodologie organizzative per una battuta esplorativa",
    "bernabei_2001.htm": "Proyecto Cuatrociénegas, Coahuila, Mexico",
    "dellerose_2001.htm": "L'Aviso Neviera (Pu 196) a Sogliano Cavour (LE)",
    "didonna_2001.htm": "Grotte e Speleologia del Costa Rica",
    "manghisi4_2001.htm": 'Il Centro di Ducumentazione Speleologica "F. Orofino" presso il Museo Speleologico "F. Anelli" delle Grotte di Castellana',
    "montenegro_amatulli2001.htm": "Capreolus capreolus nella grotta del Tasso Selvaggio",
    "speleoflash_2001.htm": "Speleo-Flash",
    "2003/didonna.htm": "Corsi di Speleologia in Costarica",
    "2003/lovece.htm": "Incidente alla Grave di Polignano (Ba)",
    "2003/lovecepace.htm": "23 gennaio 1938 - 23 gennaio 2004:  \n    66° anniversario della scoperta delle Grotte di Castellana",
    "2003/manghisi5.htm": "Cavità artificiali a Monopoli (Ba)",
    "2003/manghisi6.htm": "La Cantina del Diavolo a Villers-Cotterets",
    "2003/proiettoalii.htm": "La Grave dell'Auletta (Monti Alburni, Campania)",
    "2003/sgobba2.htm": "La Foggia di Via Bini",
    "2003/x.htm": "Soci del Gruppo Puglia Grotte nel 2003",
}


def link_bollettini_index(generated: dict[str, tuple[int, str, str]]):
    """Collega, negli indici bollettino-<anno>.md già esistenti (Fase 3), ogni
    titolo in corsivo non ancora linkato alla pagina appena generata (Fase 4).
    Da eseguire DOPO build_bollettini_testo(). Scrive DIRETTAMENTE sul file
    (non passa da safe_write_text/.content-manifest.json): questi indici sono
    già protetti come "modificati a mano" (rigenerati a suo tempo da
    build_bollettini(), poi corretti a mano in sessioni precedenti, es. i
    link aggiunti alle presentazioni PPT/PDF di Santo Tomás) -- rigenerarli da
    zero qui perderebbe quelle correzioni. Questa funzione non rigenera nulla:
    applica solo una sostituzione mirata e minima (un titolo in corsivo ->
    stesso titolo linkato) sul contenuto ATTUALE su disco, esattamente come
    farebbe una modifica a mano con l'editor -- non richiede quindi --force
    né tocca il manifest. Idempotente: se il link è già presente (rilancio),
    salta senza errori; fallisce rumorosamente solo se non trova né la forma
    sciolta né quella già linkata (fonte cambiata in modo imprevisto)."""
    by_year: dict[int, list[tuple[str, str, str]]] = {}  # anno -> [(fname, slug, span)]
    for fname, (year, slug, title) in generated.items():
        span = BOLLETTINI_INDEX_LINK_OVERRIDES.get(fname, title)
        by_year.setdefault(year, []).append((fname, slug, span))

    for year, items in sorted(by_year.items()):
        dest = BOLLETTINI_CONTENT / f"bollettino-{year}.md"
        text = dest.read_text(encoding="utf-8")
        changed = False
        for fname, slug, span in items:
            needle = f"*{span}*"
            url = f"/archivio-storico/bollettini/{year}/{slug}/"
            title_attr = span.replace("\n", " ").replace("  ", " ").strip()
            replacement = f"[*{span}*]({url} {yaml_str(title_attr)})"
            if replacement in text:
                continue
            count = text.count(needle)
            if count == 0:
                sys.exit(f"bollettino-{year}.md: titolo non trovato: {needle!r} (da {fname})")
            if count > 1:
                sys.exit(f"bollettino-{year}.md: titolo ambiguo (compare {count} volte): {needle!r} (da {fname})")
            text = text.replace(needle, replacement, 1)
            changed = True
        if changed:
            dest.write_text(text, encoding="utf-8")
            print(f"collegati i titoli in bollettino-{year}.md")


# =============================================================================
# Fase 5: gallerie fotografiche complete dei corsi (corso/<numero>/*.htm, numeri
# 23-36). Le pagine corsoNN.md già migrate (Fase 2) riportano solo un breve
# riassunto; qui sotto sta l'archivio fotografico integrale di ogni edizione,
# spesso paginato su più file nel sito originale (limite di banda dell'epoca)
# e qui riunito in un'unica pagina Hugo per corso, in ordine di file.
#
# Verificato pagina per pagina che questi file NON sono tutti gallerie pure:
# alcuni (es. corso/28/1.htm) sono resoconti narrativi di una singola uscita
# con foto intercalate, altri (es. corso/26/immagini2.htm) sono griglie di
# foto senza alcun testo. Uniti nello stesso modo (estrazione dell'intero
# <body>, non di una singola <td> come per le altre fasi -- necessario perché
# qui il contenuto reale è distribuito su più <td> fratelli allo stesso
# livello, non annidato in un unico contenitore) e lasciati a pandoc, che
# rende bene entrambi i casi: paragrafi puliti per il testo narrativo, tabella
# HTML grezza (comunque visualizzata correttamente dal browser) per le griglie
# di foto quando le celle hanno contenuto multi-riga che gfm non sa esprimere
# in Markdown puro -- stesso comportamento già verificato e accettato per la
# tabella dati catastali di bollettini/parise_2001.htm (Fase 4).
# =============================================================================

CORSI_CONTENT = REPO / "content" / "archivio-storico" / "corsi"

# 30 escluso: nessun file .htm in corso/30/, solo moduli/regolamento in PDF
# (gestiti da build_corso30_materiali, non da questa funzione).
CORSI_GALLERIA_RANGE = [23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36]

# programma.htm (23-25) è un programma di corso (materia diversa, non un
# racconto/foto di una singola giornata): pagina a sé, vedi
# build_corsi_programmi più sotto.
CORSI_GALLERIA_EXCLUDE = {"programma.htm"}

# link locali a file non immagine (pdf/doc/zip) dentro le pagine di galleria:
# rewrite_links_and_images gestisce automaticamente solo gli <img src=...>
# (jpg/gif/png), non gli <a href=...> verso altri formati -- questi restano
# altrimenti testo semplice (link tolto da strip_dead_anchors, come per
# qualunque altro link interno non riconosciuto). Trovato con una scansione
# di tutti i corso/<N>/*.htm per href locali .pdf/.doc/.zip: un solo caso
# reale (corso/33/settimana.htm, "la lezione" di Lovece per la Settimana
# della cultura speleologica).
CORSI_EXTRA_ASSETS = ["corso/33/LezioneLovece.pdf"]
for _asset in CORSI_EXTRA_ASSETS:
    LINK_REWRITE.setdefault(_asset, f"/archivio-storico/legacy/{_asset}".replace(" ", "%20"))
del _asset

NAV_LOGO_LINK_RE = re.compile(r'<a\s+href="[^"]*index_ita\.htm"[^>]*>.*?</a>', re.I | re.S)


def _discover_corso_galleria_files(n: int) -> list[str]:
    d = OLD_ROOT / "corso" / str(n)
    files = []
    for p in sorted(d.glob("*.htm")):
        if p.name.endswith("_eng.htm") or p.name in CORSI_GALLERIA_EXCLUDE:
            continue
        files.append(f"corso/{n}/{p.name}")
    return files


def _read_corso_meta(n: int) -> tuple[str, str]:
    """(titolo, data) dalla pagina corsoNN.md già migrata (Fase 2): fonte
    unica già verificata per titolo e data reale di ogni edizione."""
    text = (CORSI_CONTENT / f"corso{n}.md").read_text(encoding="utf-8")
    title_m = re.search(r'^title:\s*"(.*)"\s*$', text, re.M)
    date_m = re.search(r'^date:\s*(\S+)\s*$', text, re.M)
    return title_m.group(1), date_m.group(1)


# alcune gallerie dei corsi referenziano immagini che risultano assenti dalla
# copia di old/ fornita (es. TUTTE le 45 immagini di corso/29/festa.htm, o
# alcune di corso/31/4.htm-5.htm e corso/32/pulo.htm): non un errore di questo
# script, verificato che le cartelle stesse mancano su disco (non solo un
# problema di maiuscole/minuscole, già gestito da find_case_insensitive).
# Stesso trattamento già riservato altrove nel sito a foto mancanti dalla
# copia originale: il riferimento <img> viene tolto (non lasciato come
# immagine rotta), l'eventuale didascalia/testo intorno resta intatta.
MISSING_IMG_RE = re.compile(r'''<img\b[^>]*\bsrc=(["'])/archivio-storico/legacy/(.+?)\1[^>]*/?>''', re.I)


def _corso_image_exists(rel: str) -> bool:
    path = OLD_ROOT / rel
    return path.exists() or find_case_insensitive(path) is not None


def strip_missing_corso_images(html: str, image_refs: set[str]) -> str:
    def repl(m):
        rel = m.group(2)
        if _corso_image_exists(rel):
            return m.group(0)
        image_refs.discard(rel)
        return ""
    return MISSING_IMG_RE.sub(repl, html)


def _process_corso_fragment(src: str, image_refs: set[str]) -> str:
    raw = (OLD_ROOT / src).read_text(encoding="cp1252")
    content = extract_content(raw, "full")
    content = strip_html_comments(content)
    content = NAV_LOGO_LINK_RE.sub("", content)
    content = strip_nav_icons(content)
    content = strip_print_close_widget(content)
    content = unwrap_align_divs(content)
    content = unwrap_absolute_divs(content)
    content = resolve_mm_popups(content, src)
    content = rewrite_links_and_images(content, src, image_refs)
    content = strip_missing_corso_images(content, image_refs)
    content = strip_dead_anchors(content)
    content = strip_popup_anchors(content)
    content = simplify_bollettino_anchors(content)
    return content


def process_corso_galleria(n: int, image_refs: set[str]) -> str:
    course_title, date = _read_corso_meta(n)
    sources = _discover_corso_galleria_files(n)
    bodies = [_process_corso_fragment(src, image_refs) for src in sources]
    html = "\n<hr>\n".join(bodies)
    md = html_to_md(html)

    fm = [
        "---",
        f'title: {yaml_str(f"Archivio fotografico — {course_title}")}',
        f"date: {date}",
        'description: "Archivio fotografico completo, recuperato dal sito del Gruppo Puglia Grotte precedente a WordPress."',
        "---",
        "",
    ]
    dest = CORSI_CONTENT / str(n) / "archivio-fotografico.md"
    safe_write_text(dest, "\n".join(fm) + md + "\n")
    return f"/archivio-storico/corsi/{n}/archivio-fotografico/"


# programma.htm esiste solo per le edizioni 23-25 (le successive non hanno
# una pagina programma propria in old/, verificato con `find`).
CORSI_PROGRAMMA_RANGE = [23, 24, 25]


def process_corso_programma(n: int, image_refs: set[str]) -> str:
    course_title, date = _read_corso_meta(n)
    src = f"corso/{n}/programma.htm"
    raw = (OLD_ROOT / src).read_text(encoding="cp1252")
    content = extract_content(raw, "auto")
    content = strip_html_comments(content)
    content = NAV_LOGO_LINK_RE.sub("", content)
    content = strip_nav_icons(content)
    content = strip_print_close_widget(content)
    content = unwrap_align_divs(content)
    content = unwrap_absolute_divs(content)
    content = resolve_mm_popups(content, src)
    content = rewrite_links_and_images(content, src, image_refs)
    content = strip_dead_anchors(content)
    content = strip_popup_anchors(content)
    content = simplify_bollettino_anchors(content)
    md = html_to_md(content)

    fm = [
        "---",
        f'title: {yaml_str(f"Il programma — {course_title}")}',
        f"date: {date}",
        'description: "Pagina storica, recuperata dal sito del Gruppo Puglia Grotte precedente a WordPress."',
        "---",
        "",
    ]
    dest = CORSI_CONTENT / str(n) / "programma.md"
    safe_write_text(dest, "\n".join(fm) + md + "\n")
    return f"/archivio-storico/corsi/{n}/programma/"


def link_corso_pages(links: dict[int, list[tuple[str, str]]]):
    """Aggiunge, in coda a ogni corsoNN.md già esistente, i link alle pagine
    appena generate (archivio fotografico / programma) -- stessa logica di
    link_bollettini_index: scrittura diretta (non passa dal manifest, questi
    file sono già segnalati come modificati a mano da sessioni precedenti),
    idempotente (non ri-aggiunge un link già presente)."""
    for n, items in sorted(links.items()):
        dest = CORSI_CONTENT / f"corso{n}.md"
        text = dest.read_text(encoding="utf-8")
        changed = False
        for label, url in items:
            line = f"[{label}]({url})"
            if line in text:
                continue
            sep = "  \n" if text.endswith("  \n") or text.rstrip("\n").endswith("  ") else "\n\n"
            text = text.rstrip("\n") + "\n" + line + "  \n"
            changed = True
        if changed:
            dest.write_text(text, encoding="utf-8")
            print(f"collegate le pagine aggiuntive in corso{n}.md")


# corso/30/ non ha alcuna pagina .htm di contenuto (solo moduli/regolamento
# in PDF + il manifesto del corso in JPG): corso30.md esisteva già (Fase 2)
# con questi materiali citati come testo semplice non linkato (estratti dalla
# stessa cella "testo" di corso/corso30.htm usata per il riassunto). Questa
# funzione si limita a copiare gli asset -- il collegamento dei link nel
# testo esistente è stato fatto a mano direttamente su corso30.md (non è
# un'operazione automatizzabile in sicurezza: il testo "Regolamento pdf -
# zip" ecc. non ha una struttura ripetibile su cui costruire un pattern).
CORSO_30_MATERIALI = [
    "corso/30/GPGProgrammaXXXCorso.pdf",
    "corso/30/GPGRegolamento.pdf",
    "corso/30/GPGModuloIscrizione.pdf",
    "corso/30/GPGliberatoriafoto.pdf",
    "corso/30/SSIModuloISCRIZIONE.pdf",
    "corso/30/CSXXXCorso.pdf",
    "corso/30/images/manifesto.jpg",
]


def build_corso30_materiali():
    direct_assets = set(CORSO_30_MATERIALI)
    copy_assets(set(), direct_assets=direct_assets)
    for rel in direct_assets:
        LINK_REWRITE.setdefault(rel, f"/archivio-storico/legacy/{rel}".replace(" ", "%20"))


def build_corsi_gallerie():
    image_refs: set[str] = set()
    links: dict[int, list[tuple[str, str]]] = {}
    for n in CORSI_GALLERIA_RANGE:
        url = process_corso_galleria(n, image_refs)
        links.setdefault(n, []).append(("Archivio fotografico completo", url))
    for n in CORSI_PROGRAMMA_RANGE:
        url = process_corso_programma(n, image_refs)
        links.setdefault(n, []).append(("Il programma", url))
    copy_assets(image_refs, direct_assets=set(CORSI_EXTRA_ASSETS))
    save_manifest()
    link_corso_pages(links)
    build_corso30_materiali()

    if warnings:
        print("\n== Avvisi ==")
        for w in warnings:
            print(f"- {w}")


# =============================================================================
# Fase 6: pagine orfane scoperte in un nuovo censimento di old/ dopo il
# completamento delle Fasi 1-5, mai referenziate né dal resto di old/ già
# migrato né dal vero content/ WordPress. Copre la Fase H del piano
# (dettagli del Museo Speleologico Franco Anelli) e la Fase A-bis (residuo
# di pagine orfane collegate a contenuto già migrato, stesso pattern della
# Fase A originale: sotto-pagine mai seguite, popup non aperti la prima
# volta). Verificato pagina per pagina con extract_content(..., "auto") che
# tutte estraggono contenuto reale sensato prima di scriverle.
#
# attivi/preveticelli.htm ESCLUSA di proposito: "(Foto di , testo di )" con
# i campi vuoti e nessuna immagine nella galleria sottostante -- una pagina
# mai completata nemmeno sul sito originale, non solo mai linkata. Nessun
# dato reale da recuperare, quindi nessun placeholder (non fa parte di
# alcuna sezione/indice visibile che ne renderebbe evidente l'assenza).
# =============================================================================

LINK_REWRITE["esplorazioni/monopoli.htm"] = "/archivio-storico/esplorazioni/monopoli/"
LINK_REWRITE["esplorazioni/monopoli2.htm"] = "/archivio-storico/esplorazioni/monopoli-rilievo/"
LINK_REWRITE["esplorazioni/fotomonopoli.htm"] = "/archivio-storico/esplorazioni/monopoli-reportage-fotografico/"

# esplorazioni/monopoli2.htm incorpora un iframe YouTube (il "video di
# Giampaolo Pinto" citato nel testo): niente embed di terzi su un sito
# statico (stessa policy già applicata altrove nel progetto), ma il link
# reale al video resta, non va perso.
SOURCE_PATCHES["esplorazioni/monopoli2.htm"] = (
    '<iframe width="420" height="315" src="http://www.youtube.com/embed/dSYiPXdHsxo" frameborder="0" allowfullscreen></iframe>',
    '<a href="https://www.youtube.com/watch?v=dSYiPXdHsxo" target="_blank" title="Video di Giampaolo Pinto">Il video di Giampaolo Pinto</a> (YouTube)',
)
# "Minevino Murge" per "Minervino Murge" (comune reale, BAT): refuso genuino
# e coerente nel sorgente (compare così sia nel calendario sia nel corpo
# dell'articolo, mai "Minervino"), corretto qui.
SOURCE_PATCHES["attivi/volpe.htm"] = ("Minevino Murge", "Minervino Murge")

FASE_H_A_BIS_DIRECT_ASSETS = [
    "esplorazioni/monopoli/relazionefinale.pdf",
    "esplorazioni/monopoli/TRASMISSIONERILIEVIMONOPOLI.pdf",
]
for _asset in FASE_H_A_BIS_DIRECT_ASSETS:
    LINK_REWRITE.setdefault(_asset, f"/archivio-storico/legacy/{_asset}")
del _asset

FASE_H_A_BIS_PAGES = [
    # --- Fase A-bis: residuo di pagine orfane ---
    dict(slug="soci-scomparsi/dino-faiano", title="Chi era Dino Faiano?",
         sources=["faianochi.htm"], mode="auto", date=DATE_RIMIGRAZIONE),
    dict(slug="esplorazioni/monopoli-rilievo", title="Il rilievo nel sottosuolo di Monopoli",
         sources=["esplorazioni/monopoli2.htm"], mode="auto", date="2010-12-11"),
    dict(slug="esplorazioni/monopoli-reportage-fotografico",
         title="Il reportage fotografico del rilievo nei rifugi antiaerei di Monopoli",
         sources=["esplorazioni/fotomonopoli.htm"], mode="auto", date="2010-12-11"),
    # nidificate sotto programma-2006-2007/, come le altre uscite dello
    # stesso calendario già migrate in Fase A (angelo/braca/laterza/notarvincenzo).
    dict(slug="programma-2006-2007/grotta-della-volpe", title="Grotta della Volpe",
         sources=["attivi/volpe.htm"], mode="auto", date="2006-12-17"),
    dict(slug="programma-2006-2007/pulo-di-altamura", title="Inghiottitoio del Pulo di Altamura",
         sources=["attivi/pulo.htm"], mode="auto", date="2006-11-26"),
]

# --- Fase H: Museo Speleologico Franco Anelli, sezioni di dettaglio ---
# Ogni pagina condivide lo stesso template: una <td> di navigazione a schede
# JS ("La storia"/"Attività"/"La rivista", link museo.htm?storia ecc. --
# chrome puro, tre etichette fisse ripetute identiche su tutte e sei le
# pagine, mai ancore reali) seguita dal contenuto vero. La posizione della
# cella di contenuto rispetto a quella di navigazione NON è uniforme --
# verificato: in alcune pagine (es. museo_percorso.htm) è la <td> SORELLA
# nella stessa <table>, in altre (es. museo_catalogo.htm) è un <div
# id="dove"...position:absolute...> che segue l'intera <table> di
# navigazione -- quindi si toglie solo la <td> di navigazione stessa (mai
# l'intera <table>, che in alcuni casi conterrebbe anche il contenuto vero
# nella cella accanto). L'indirizzo del museo (stesso <div id="dove"> in
# ogni pagina, già presente su museo.md, la pagina madre) è tolto a parte.
MUSEO_NAV_TD_RE = re.compile(
    r'<td\b(?:(?!</td>).)*?museo\.htm\?storia(?:(?!</td>).)*?</td>',
    re.I | re.S,
)
MUSEO_ADDRESS_DIV_RE = re.compile(r'<div\s+id="dove"[^>]*>.*?</div>', re.I | re.S)
# variante "torna su" propria di questi file: tre <b>^</b> separati da <br>
# (non un singolo <b> con "^^^"/"^ Torna su ^" come nelle pagine dei
# bollettini, già gestite da BACK_TO_TOP_RE -- pattern diverso, non riusabile).
MUSEO_BACK_TO_TOP_RE = re.compile(
    r'(<br\s*/?>\s*)*<div[^>]*align="right"[^>]*>\s*<a\b[^>]*href="#(?:up|top)"[^>]*>'
    r'(?:\s*<b>[^<]*\^[^<]*</b>\s*(?:<br\s*/?>)?)+\s*</a>\s*</div>',
    re.I | re.S,
)
# dopo aver tolto la <td> di navigazione, in alcune pagine (es.
# museo_catalogo.htm) resta un guscio di tabella con celle ormai vuote (il
# contenuto vero era altrove, in un <div id="dove"> già tolto sopra):
# pandoc lo renderebbe come una tabella Markdown vuota.
MUSEO_EMPTY_TABLE_RE = re.compile(
    r'<table\b[^>]*>(?:\s|<colgroup>.*?</colgroup>|</?tbody>|<tr[^>]*>|</tr>|<td[^>]*>\s*</td>)*</table>',
    re.I | re.S,
)


def strip_museo_tab_chrome(html: str) -> str:
    html = MUSEO_NAV_TD_RE.sub("", html)
    html = MUSEO_ADDRESS_DIV_RE.sub("", html)
    html = MUSEO_BACK_TO_TOP_RE.sub("", html)
    html = MUSEO_EMPTY_TABLE_RE.sub("", html)
    return html


def process_museo_page(page: dict, image_refs: set[str], date: str):
    bodies = []
    for src in page["sources"]:
        raw = (OLD_ROOT / src).read_text(encoding="iso-8859-1")
        content = extract_content(raw, page["mode"])
        content = strip_html_comments(content)
        content = strip_nav_icons(content)
        content = strip_museo_tab_chrome(content)
        content = strip_print_close_widget(content)
        content = unwrap_absolute_divs(content)
        content = resolve_mm_popups(content, src)
        content = rewrite_links_and_images(content, src, image_refs)
        content = strip_dead_anchors(content)
        content = strip_popup_anchors(content)
        bodies.append(content)
    html = "\n<hr>\n".join(bodies)
    md = html_to_md(html)
    # &#10; comparso nell'output di pandoc (non nel sorgente, verificato) in
    # corrispondenza di alcuni <br> dentro l'HTML grezzo che pandoc non sa
    # esprimere altrimenti -- stesso artefatto già corretto a mano in
    # corso30.md, qui tolto in automatico.
    md = md.replace("&#10;", "")

    fm = [
        "---",
        f"title: {yaml_str(page['title'])}",
        f"date: {date}",
        'description: "Pagina storica, recuperata dal sito del Gruppo Puglia Grotte precedente a WordPress."',
        "---",
        "",
    ]
    dest = CONTENT / f"{page['slug']}.md"
    safe_write_text(dest, "\n".join(fm) + md + "\n")


MUSEO_DETAIL_PAGES = [
    # stessa data convenzionale di museo.md (2000-01-23), pagine descrittive
    # senza una data reale propria, come la pagina madre di cui sono dettaglio.
    dict(slug="museo-percorso", title="Il percorso museale",
         sources=["museo_percorso.htm"], mode="auto", date="2000-01-23"),
    dict(slug="museo-laboratorio", title="Il laboratorio di biospeleologia e mineralogia",
         sources=["museo_labo.htm"], mode="auto", date="2000-01-23"),
    # "spelologica" nel <title> originale è un refuso genuino (verificabile:
    # il resto del sito scrive sempre "speleologica"), corretto qui.
    dict(slug="museo-centro-documentazione", title="Il Centro di documentazione speleologica Franco Orofino",
         sources=["museo_biblio.htm"], mode="auto", date="2000-01-23"),
    dict(slug="museo-catalogo", title="Catalogo del museo",
         sources=["museo_catalogo.htm"], mode="auto", date="2000-01-23"),
    dict(slug="museo-archivio-iconografico", title="Archivio iconografico delle Grotte di Castellana",
         sources=["museo_archivio.htm"], mode="auto", date="2000-01-23"),
    dict(slug="museo-e-finalmente", title="E finalmente…",
         sources=["museo_sogno.htm"], mode="auto", date="2000-01-23"),
]


def build_fase_h_a_bis():
    image_refs: set[str] = set()
    for page in FASE_H_A_BIS_PAGES:
        process_page(page, image_refs, date=page["date"])
    for page in MUSEO_DETAIL_PAGES:
        process_museo_page(page, image_refs, date=page["date"])
    copy_assets(image_refs, direct_assets=set(FASE_H_A_BIS_DIRECT_ASSETS))
    save_manifest()
    export_link_rewrite()

    if warnings:
        print("\n== Avvisi ==")
        for w in warnings:
            print(f"- {w}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--extend":
        extend_archive()
    elif len(sys.argv) > 1 and sys.argv[1] == "--bollettini":
        build_bollettini()
    elif len(sys.argv) > 1 and sys.argv[1] == "--bollettini-testo":
        generated = build_bollettini_testo()
        link_bollettini_index(generated)
    elif len(sys.argv) > 1 and sys.argv[1] == "--corsi-gallerie":
        build_corsi_gallerie()
    elif len(sys.argv) > 1 and sys.argv[1] == "--fase-h-a-bis":
        build_fase_h_a_bis()
    else:
        main()
