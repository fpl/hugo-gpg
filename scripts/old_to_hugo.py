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
    "attivi/programma0607.htm": "/archivio-storico/programma-2006-2007/",
    "convreg/programma.htm": "/archivio-storico/iii-convegno-speleologia-pugliese/",
    "corso/corsoalburni.htm": "/archivio-storico/corso-alburni/",
    "santomas/chi.htm": "/archivio-storico/progetto-santo-tomas/",
    "santomas/perche.htm": "/archivio-storico/progetto-santo-tomas/",
    "santomas/dove.htm": "/archivio-storico/progetto-santo-tomas/",
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
        path.write_text(text.replace(find, repl), encoding="utf-8")
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
    dict(slug="spelaion-2011", title="Spélaion 2011 — XVI Incontro di Speleologia Regionale",
         sources=["eventi/spelaion2011.htm"], mode="testo"),
    dict(slug="programma-2006-2007", title="Programma attività speleologica autunno-inverno 2006-2007",
         sources=["attivi/programma0607.htm"], mode="testo"),
    dict(slug="iii-convegno-speleologia-pugliese", title="III Convegno di Speleologia Pugliese — Il Programma",
         sources=["convreg/programma.htm"], mode="body"),
    dict(slug="corso-alburni", title="Corso di I livello di Speleologia sui Monti Alburni",
         sources=["corso/corsoalburni.htm"], mode="testo"),
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
    "images/convreg1992.jpg", "images/convreg85.jpg", "images/on.gif",
    "images/q_1985_little.jpg", "images/q_1986_little.jpg", "images/q_1987_little.jpg",
    "images/q_1995_little.jpg",
    "GruppoPugliaGrotteCatalogoBiblioteca2013.zip",
]

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


def extract_content(raw: str, mode: str) -> str:
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
    CONTENT.mkdir(parents=True, exist_ok=True)
    (CONTENT / "_index.md").write_text(
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
        encoding="utf-8",
    )
    print(f"scritto {(CONTENT / '_index.md').relative_to(REPO)}")


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
        content = strip_print_close_widget(content)
        content = unwrap_absolute_divs(content)
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
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(fm) + md + "\n", encoding="utf-8")
    print(f"scritto {dest.relative_to(REPO)}")


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
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
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
        encoding="utf-8",
    )
    print(f"scritto {dest.relative_to(REPO)}")


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

    if warnings:
        print("\n== Avvisi ==")
        for w in warnings:
            print(f"- {w}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--extend":
        extend_archive()
    else:
        main()
