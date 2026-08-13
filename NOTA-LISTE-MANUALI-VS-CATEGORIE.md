# Nota: liste manuali nelle pagine di sezione vs. tassonomia "categorie"

Osservazione emersa controllando `content/eventi/_index.md`: la lista puntata in cima
alla pagina è più corta ed è diversa sia dalle sotto-pagine elencate subito sotto, sia
dall'elenco che si ottiene cliccando sulla voce "Eventi" nel widget Categorie della
sidebar. Non è un difetto della migrazione: è un comportamento ereditato dal sito
WordPress originale, verificato anche in `content/esplorazioni/nazionali/_index.md`.

## Il problema

Nelle pagine di sezione che vengono da una pagina statica WordPress con figli (`eventi`,
`esplorazioni/nazionali`, `chi-siamo`, `corsi`, `pubblicazioni`, ...), su una stessa
pagina Hugo convivono **tre liste indipendenti**, popolate da tre meccanismi diversi che
in WordPress non erano mai stati tenuti sincronizzati tra loro:

1. **Il corpo della pagina** (`.Content` in `layouts/_default/list.html`) — testo
   scritto a mano nell'editor WordPress della pagina originale (es. pagina id 18 per
   "Eventi"). È un elenco "punti salienti" curato manualmente, che può linkare
   liberamente a post (`novita/`), corsi, o altre sezioni — non necessariamente ai
   propri figli. Nel caso di `eventi/` e `esplorazioni/nazionali/`, l'ultimo
   aggiornamento manuale risale rispettivamente al 2015 e al 2012: da allora nessuno
   ha più toccato quel testo.
2. **Le sotto-pagine reali** (`.Pages` nello stesso template) — i figli gerarchici
   veri della pagina WordPress, elencati automaticamente da Hugo. Sono in numero
   diverso dalla lista 1 perché rispondono a una logica strutturale (parent → child
   page), non editoriale.
3. **La tassonomia "categorie"** (widget "Categorie" in `layouts/partials/sidebar-
   scheda.html`, righe 35-40) — applicata a livello di singolo post in `content/
   novita/*.md` (`categories: [...]` nel front matter), copiata 1:1 da
   `wp_term_relationships` nel DB WordPress. Riguarda solo i `post_type=post`, mai le
   pagine statiche, ed è mantenuta post per post da chi scriveva la notizia, non da
   chi curava la pagina di sezione.

## Perché succede (causa nel WP originale, non nella migrazione)

WordPress non ha mai offerto un meccanismo che tenesse automaticamente sincronizzati
questi tre elenchi: sono tre funzionalità del CMS scelte e popolate da persone/momenti
diversi.
`scripts/wp_to_hugo.py` ha correttamente riportato 1:1 tutti e tre i meccanismi (corpo
pagina via pandoc, gerarchia figli via `PAGE_MAP`, categorie via front matter) — la
migrazione non ha introdotto la discrepanza, l'ha solo resa più visibile perché ora le
tre liste sono a un click di distanza sulla stessa pagina, mentre nel tema WordPress
originale erano meno ravvicinate visivamente.

## Dove si manifesta

Solo due categorie esistono in `content/novita/` oltre alla generica "Novità": `Eventi`
e `Nazionali`. Sono quindi le uniche due sezioni dove può presentarsi lo scarto
"lista manuale obsoleta vs. categoria aggiornata":

| sezione | link manuali nel corpo | sotto-pagine reali | post con categoria omonima |
|---|---|---|---|
| `eventi/` | 6 (fermi al 2015) | 4 | 8 |
| `esplorazioni/nazionali/` | 57 (fermi al 2012) | 5 | 2 (corretto: v. sotto) |

Per le altre sezioni di primo livello (`chi-siamo`, `corsi`, `esplorazioni`, `museo`,
`pubblicazioni`, `esplorazioni/internazionali`) il numero di link manuali nel corpo non
coincide comunque col numero di sotto-pagine, ma è normale: quei link puntano
deliberatamente altrove (post, altre sezioni) e non esiste una categoria omonima con cui
confrontarli, quindi non c'è un contenuto "silenziosamente assente" da un elenco che
sembra essere l'indice completo.

## Intervento già fatto

`esplorazioni/nazionali/_index.md`: aggiunti a mano i due post 2015 e 2017 che avevano
la categoria "Nazionali" ma non comparivano nella lista manuale (fermatasi al 2012).
Scelta minima e conservativa: nessuna riscrittura strutturale, solo le due righe
mancanti, verificate con build Hugo + controllo HTTP + screenshot.

`eventi/_index.md` non è stato ancora toccato: la lista manuale lì è più corta (6 link)
rispetto agli 8 post con categoria "Eventi", quindi lo stesso tipo di intervento
manuale si applicherebbe, ma non è stato fatto — da valutare (vedi sotto).

## Misure possibili

Nessuna di queste è stata scelta al posto dell'utente; sono opzioni, non un piano
deciso.

1. **Non fare nulla, solo documentare** (questo file). Il comportamento è fedele
   all'originale WordPress e non è un errore di migrazione; un lettore che clicca sul
   widget Categorie trova comunque l'elenco completo.
2. **Riconciliazione manuale una tantum**, come già fatto per `esplorazioni/nazionali/`:
   aggiungere a `eventi/_index.md` gli eventuali post mancanti. Basso sforzo, ma è un
   intervento "una tantum" che si disallineerà di nuovo al primo nuovo post taggato
   `Eventi` scritto in futuro senza aggiornare anche l'indice manuale.
3. **Automatizzare la lista in coda al testo manuale**: nel template
   `layouts/_default/list.html`, dopo `.Content`, aggiungere un blocco che elenca
   automaticamente `where .Site.RegularPages "Section" "novita"` filtrati per
   `.Params.categories` uguale al nome della sezione corrente (quando esiste una
   categoria con lo stesso nome) — stesso pattern già usato per Archivi/Categorie in
   `sidebar-scheda.html`. Elimina il problema alla radice e resta sempre aggiornato,
   ma cambia il layout della pagina (va deciso se è un cambiamento voluto rispetto al
   fedele "com'era" del tema Twenty Thirteen).
4. **Sostituire la lista manuale con quella automatica**, invece di affiancarle:
   più pulito ma perde le voci del testo manuale che non hanno un post/categoria
   corrispondente (es. i link a `corsi/`, `esplorazioni/` dentro `eventi/_index.md`) —
   richiederebbe prima verificare che nessuna di quelle voci sia effettivamente persa.

Nessuna misura è stata applicata oltre alla 2 per `esplorazioni/nazionali/`. Decidere
se e come intervenire su `eventi/` (e se adottare la 3/4 come convenzione per il resto
del sito) resta una scelta dell'utente.
