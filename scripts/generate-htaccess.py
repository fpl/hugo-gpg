#!/usr/bin/env python3
"""Genera static/.htaccess con un redirect 301 per ogni "aliases:" reale nel
front matter di content/**/*.md (i vecchi URL WordPress, prefisso /home/,
verso i nuovi permalink Hugo). Vedi "Prossimi passi consigliati" #3 in
README.md per il perché: gli "aliases:" di Hugo generano solo una pagina
statica con <meta http-equiv="refresh"> (funziona per l'utente, ma non è un
vero redirect HTTP 301 -- più debole per SEO).

Usa la mappatura calcolata da Hugo stesso (.Aliases / .Permalink in un
output format dedicato, scripts/htaccess-extra.toml + layouts/
index.aliasdump.txt) invece di riparsare a mano lo YAML: gestisce
correttamente eventuali slug/permalink personalizzati.

Uso: python3 scripts/generate-htaccess.py
Rigenera static/.htaccess. Nessuna dipendenza pip, nessun effetto sulla
build normale (usa una destinazione --destination temporanea, mai public/).
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTACCESS_PATH = REPO / "static" / ".htaccess"

SPECIAL_CHARS = re.compile(r'[.^$*+?()\[\]{}|\\]')


def main():
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

    pairs: dict[str, str] = {}
    conflicts = []
    for line in lines:
        old, new = line.split("|", 1)
        if old in pairs and pairs[old] != new:
            conflicts.append((old, pairs[old], new))
        pairs[old] = new
    if conflicts:
        for old, a, b in conflicts:
            print(f"CONFLITTO: {old} -> {a} E {b}", file=sys.stderr)
        sys.exit("Alias duplicati con destinazioni diverse: risolvere prima di generare.")

    for old in pairs:
        if SPECIAL_CHARS.search(old):
            sys.exit(f"Percorso con caratteri speciali per regex, non gestito: {old}")

    out = [
        "# Redirect 301 dai vecchi URL WordPress (prefisso /home/, dove girava",
        "# WordPress) ai nuovi permalink Hugo. Generato da scripts/generate-htaccess.py",
        '# a partire dagli "aliases:" nel front matter di content/**/*.md -- non',
        "# scritto a mano: se cambia un permalink, rilanciare lo script invece di",
        "# editare qui (le modifiche manuali verrebbero perse al prossimo rilancio).",
        "#",
        "# RedirectMatch (non Redirect): match esatto per regex ancorata (^...$),",
        "# non prefisso -- evita che una regola più corta (es. /home/corsi/) intercetti",
        "# per errore richieste più specifiche (es. /home/corsi/52-corso-.../) in base",
        "# all'ordine delle direttive.",
        "",
    ]
    for old, new in sorted(pairs.items()):
        pattern = "^" + old.rstrip("/") + "/?$"
        out.append(f"RedirectMatch 301 {pattern} {new}")

    HTACCESS_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"scritto {HTACCESS_PATH.relative_to(REPO)} ({len(pairs)} redirect)")


if __name__ == "__main__":
    main()
