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
3. Homepage del sito pre-WordPress, tutte le varianti reali (lingua/
   risoluzione) trovate in old/ -- non tracciate da LINK_REWRITE perché non
   linkate da nessun contenuto migrato, ma redirigerle alla home ha un
   destinatario ovvio e certo. Escluse le varianti "*OLD.htm" (superate,
   stessa esclusione già documentata in README per il resto di old/).

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

# Varianti reali della homepage pre-WordPress trovate in old/ (verificato con
# `ls old/www.gruppopugliagrotte.it/index*.htm`), escluse le "*OLD.htm".
OLD_HOMEPAGE_VARIANTS = [
    "index.htm", "index_ita.htm", "index_eng.htm",
    "index1024.htm", "index1024_ita.htm", "index1024_eng.htm",
]


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


def get_homepage_pairs(base_url: str) -> dict[str, str]:
    """3. Varianti della vecchia homepage -> nuova home."""
    return {"/" + name: base_url + "/" for name in OLD_HOMEPAGE_VARIANTS}


def main():
    base_url = get_base_url()
    sources = [
        ("WordPress (/home/...)", get_wp_era_pairs()),
        ("pre-WordPress (LINK_REWRITE)", get_pre_wp_pairs(base_url)),
        ("homepage pre-WordPress", get_homepage_pairs(base_url)),
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
