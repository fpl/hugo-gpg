
# La lista dei TODO per la migrazione

* Riupensare l'organizzazione tematica e in particolare gli indici sulle pagine che rimandano a semplici post (per es. Eventi, Pubblicazioni): mentre un indice ha poca ragione di essere presente, una intro ragionata che rimanda ad alcuni eventi potrebbe avere una ragione di essere, se aggiunge valore.
* Occorre validare le conversioni automatiche via pandoc, sono ancora visibili artefatti legati ai layout originali dei vecchi contenuti.
* Andrebbero visitati i markdown di archivio storico e del restante sito in relazione ai vecchi contenuti in modo da avere layout più puliti. Lista dettagliata delle pagine coinvolte, pagina già sistemata come modello, e un avviso importante su un tentativo di farlo in blocco via script che è andato storto: vedi `NOTA-PULIZIA-ARTEFATTI-PANDOC.md`.
  * Tra questi artefatti: ~15 pagine (concentrate in `content/pubblicazioni/` e
    `content/eventi/`) hanno ancora `style="color: #000000"` (e poche varianti
    `Maroon`/`#660033`/`#0070BA`) inline, sopravvissuti da HTML Dreamweaver via
    pandoc. Dal supporto tema chiaro/scuro (branch `darkmode`), `static/css/
    style.css` neutralizza questi colori con una regola `!important` scoped a
    `.prose` in dark mode (altrimenti sarebbe testo nero illeggibile su sfondo
    scuro) — la regola nasconde il sintomo ma non tocca il markup: non
    scambiare "leggibile in dark mode" per "pulito", l'HTML grezzo va ancora
    ripulito qui come nel resto della lista.
* Diverse sezioni di archivio-storico non sono sviluppate, vedi piano separato di dettaglio.
