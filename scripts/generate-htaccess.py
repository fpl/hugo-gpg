#!/usr/bin/env python3
"""Genera static/.htaccess con un redirect 301 per ogni URL del sito vecchio
di cui conosciamo la destinazione reale. Vedi "Prossimi passi consigliati" #3
in README.md per il perché: gli "aliases:" di Hugo generano solo una pagina
statica con <meta http-equiv="refresh"> (funziona per l'utente, ma non è un
vero redirect HTTP 301 -- più debole per SEO).

Tre fonti, tre epoche del sito:

1. WordPress (prefisso /home/, dove girava) -> nuovi permalink Hugo: dagli
   "aliases:" nel front matter di content/**/*.md, letti tramite Hugo stesso
   (.Aliases / .Permalink in un output format dedicato, scripts/
   htaccess-extra.toml + layouts/index.aliasdump.txt) invece di riparsare a
   mano lo YAML -- gestisce correttamente eventuali slug personalizzati (es.
   /home/chi-siamo/il-consiglio-direttivo/ -> .../chi-siamo/consiglio-direttivo/,
   dove lo slug stesso è cambiato, non solo la sezione).
2. Sito pre-WordPress (bare root, es. /museo.htm -- vedi CLAUDE.md: quella
   copia era la webroot stessa) -> content/archivio-storico/: da
   scripts/old_to_hugo.py:LINK_REWRITE, la stessa mappatura che lo script usa
   per riscrivere i link interni. Esclusa "old-index.htm": chiave sintetica
   per un href malformato nel sorgente originale, non un URL mai esistito
   davvero (vedi commento su LINK_REWRITE).

NON generato (deliberatamente): redirect verso la home ("/") per le vecchie
varianti di index.htm del sito pre-WordPress. Provato il 16/08/2026 e
rimosso subito dopo un incidente in produzione: con quelle 6 regole
presenti, QUALUNQUE richiesta alla home (non solo alle vecchie varianti)
entrava in un loop di redirect 301 su se stessa -- isolato per bisezione
diretta contro il server reale (rimuovendo prima l'intero .htaccess, poi
reintroducendo le regole per gruppi), non riprodotto localmente né spiegato
del tutto (sospetto: un'interazione tra RedirectMatch con target uguale alla
document root e la gestione di mod_dir/DirectoryIndex su questo hosting, ma
non verificato lato server -- nessun accesso alla configurazione Apache di
Aruba oltre FTP). Per 6 vecchi nomi file di homepage, praticamente mai
linkati da fuori, il rischio non vale il beneficio: se serve in futuro,
testare PRIMA su un URL di prova non-root, mai direttamente su "/".

4. Eccezione singola e mirata alla regola precedente: "/home/" (bare, senza
   sotto-percorso) -> "/". A differenza delle 6 varianti rimosse, qui la
   sorgente non è un nome di file storico che potrebbe coincidere con una
   DirectoryIndex candidate di Apache -- è una directory reale rimasta sul
   server dai tempi di WordPress (era la webroot dell'installazione), oggi
   senza index e con "Options -Indexes": chi la richiede riceve un 403 nudo
   invece di un redirect, perché la vecchia home page di WordPress
   (show_on_front=posts) non aveva un id pagina e quindi nessun alias in
   PAGE_MAP -- unico caso mai coperto dalle altre 168 regole, che coprono
   tutte "/home/<slug>/". Verificato il 16/08/2026 che "/home/<slug>/"
   funziona correttamente già da 168 regole analoghe (nessun loop): il
   meccanismo RedirectMatch su questo hosting è quindi affidabile in
   generale, il problema del punto precedente era specifico alle vecchie
   varianti di index.htm. Deployata da sola e verificata con richieste
   ripetute a "/" prima di considerarla stabile.

Uso: python3 scripts/generate-htaccess.py
Rigenera static/.htaccess. Nessuna dipendenza pip, nessun effetto sulla
build normale (usa una destinazione --destination temporanea, mai public/).
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTACCESS_PATH = REPO / "static" / ".htaccess"

# Chiavi di LINK_REWRITE senza un vero URL storico corrispondente (vedi
# commento sulla costante nello script stesso), o con un nome file che
# contiene spazi letterali: il redirect risultante dipenderebbe da come
# Apache decodifica %20 prima del match con RedirectMatch, mai verificato
# contro il server reale -- per un solo allegato PDF non vale il rischio di
# una regola non testata in produzione, meglio ometterla (nessuna regressione:
# senza, quell'URL storico resta un 404 come lo è oggi, non peggio).
LINK_REWRITE_SYNTHETIC_KEYS = {
    "old-index.htm",
    "esplorazioni/alburni/CS fine campo Alburni 2012.pdf",
}

def get_base_url() -> str:
    text = (REPO / "hugo.toml").read_text(encoding="utf-8")
    m = re.search(r'^baseURL\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        sys.exit("baseURL non trovato in hugo.toml")
    return m.group(1).rstrip("/")


def get_wp_era_pairs() -> dict[str, str]:
    """1. Aliases WordPress (/home/...) -> permalink Hugo, via Hugo stesso."""
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            ["hugo", "--config", "hugo.toml,scripts/htaccess-extra.toml",
             "--destination", tmp, "--minify"],
            cwd=REPO, capture_output=True, text=True,
        )
        if r.returncode != 0:
            sys.exit(f"Errore hugo: {r.stderr}")
        dump_path = Path(tmp) / "aliasdump.txt"
        if not dump_path.exists():
            sys.exit("aliasdump.txt non generato: controlla scripts/htaccess-extra.toml "
                      "e layouts/index.aliasdump.txt")
        lines = [l.strip() for l in dump_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    pairs = {}
    for line in lines:
        old, new = line.split("|", 1)
        pairs[old] = new
    return pairs


def get_pre_wp_pairs(base_url: str) -> dict[str, str]:
    """2. Pagine/asset pre-WordPress (bare root) -> content/archivio-storico/,
    via LINK_REWRITE dello script di migrazione."""
    sys.path.insert(0, str(REPO / "scripts"))
    import old_to_hugo as m
    pairs = {}
    for old_rel, new_path in m.LINK_REWRITE.items():
        if old_rel in LINK_REWRITE_SYNTHETIC_KEYS:
            continue
        pairs["/" + old_rel] = base_url + new_path
    return pairs


def get_bare_home_pair(base_url: str) -> dict[str, str]:
    """4. "/home/" (bare) -> "/": vedi punto 4 nel docstring del modulo."""
    return {"/home": base_url + "/"}


def main():
    base_url = get_base_url()
    sources = [
        ("WordPress (/home/...)", get_wp_era_pairs()),
        ("pre-WordPress (LINK_REWRITE)", get_pre_wp_pairs(base_url)),
        ("home bare (/home/ -> /)", get_bare_home_pair(base_url)),
    ]

    pairs: dict[str, str] = {}
    conflicts = []
    for label, src_pairs in sources:
        for old, new in src_pairs.items():
            if old in pairs and pairs[old] != new:
                conflicts.append((old, pairs[old], new, label))
                continue
            pairs[old] = new
    if conflicts:
        for old, a, b, label in conflicts:
            print(f"CONFLITTO ({label}): {old} -> {a} E {b}", file=sys.stderr)
        sys.exit("Percorsi duplicati con destinazioni diverse: risolvere prima di generare.")

    host = re.sub(r"^https?://", "", base_url).rstrip("/")

    out = [
        "# Forza HTTPS. Verificato il 16/08/2026: http://www.gruppopugliagrotte.it/",
        "# risponde 200 in chiaro oggi (Aruba non lo fa automaticamente a monte) --",
        "# questa regola ha quindi un effetto reale, non è solo difesa in profondità.",
        "# Ripresa dal vecchio .htaccess WordPress, che redirigeva anche sotto /home/:",
        "# scartata quella parte, non più pertinente (il ponte verso WordPress non",
        "# serve più, tutto il sito vive già alla webroot con Hugo).",
        "RewriteEngine On",
        "RewriteCond %{HTTPS} off",
        rf"RewriteCond %{{HTTP_HOST}} ^(www\.)?{re.escape(host.removeprefix('www.'))}$",
        "RewriteRule ^(.*)$ https://%{HTTP_HOST}/$1 [R=301,L]",
        "",
        "# Redirect 301 dai vecchi URL del sito (WordPress sotto /home/, e",
        "# prima ancora un sito statico servito dalla webroot stessa) ai nuovi",
        "# permalink Hugo. Generato da scripts/generate-htaccess.py -- non scritto",
        "# a mano: se cambia un permalink, rilanciare lo script invece di editare",
        "# qui (le modifiche manuali verrebbero perse al prossimo rilancio).",
        "#",
        "# RedirectMatch (non Redirect): match esatto per regex ancorata (^...$),",
        "# non prefisso -- evita che una regola più corta (es. /home/corsi/) intercetti",
        "# per errore richieste più specifiche (es. /home/corsi/52-corso-.../) in base",
        "# all'ordine delle direttive.",
        "",
    ]
    for old, new in sorted(pairs.items()):
        # re.escape sui percorsi con un punto letterale (es. i vecchi .htm
        # pre-WordPress): senza, "." in regex significa "qualsiasi carattere",
        # non il punto letterale del nome file.
        pattern = "^" + re.escape(old.rstrip("/")) + "/?$"
        out.append(f"RedirectMatch 301 {pattern} {new}")

    HTACCESS_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    for label, src_pairs in sources:
        print(f"  {label}: {len(src_pairs)}")
    print(f"scritto {HTACCESS_PATH.relative_to(REPO)} ({len(pairs)} redirect totali)")


if __name__ == "__main__":
    main()
