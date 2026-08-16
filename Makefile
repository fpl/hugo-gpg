# Makefile — build e pubblicazione del sito Hugo di gruppopugliagrotte.it
#
# Le credenziali FTP NON vanno scritte qui: vanno in un file locale
# ".env.ftp" (vedi .env.ftp.example), incluso solo se presente e mai
# stampato a video da questo Makefile.

HUGO ?= hugo
BUILD_DIR := public

-include .env.ftp
export

# --- Aruba: parametri di connessione FTP (sovrascrivibili da .env.ftp) -----
# ftps è obbligatorio (il piano Aruba non accetta ftp in chiaro).
FTP_PROTOCOL ?= ftps
FTP_HOST     ?=
FTP_USER     ?=
FTP_PASS     ?=
FTP_REMOTE_DIR ?= /

.PHONY: help build build-drafts build-future build-all \
        serve serve-prod clean publish publish-dry-run check-ftp-vars

help:
	@echo "Target disponibili:"
	@echo "  make build          - build di produzione (niente bozze, niente contenuto futuro)"
	@echo "  make build-drafts   - build includendo le pagine draft: true"
	@echo "  make build-future   - build includendo le pagine con date future"
	@echo "  make build-all      - build con bozze + contenuto futuro (draft + future)"
	@echo "  make serve          - server locale su :1313 con bozze e contenuto futuro"
	@echo "  make serve-prod     - server locale su :1313, solo contenuto pubblicabile ora"
	@echo "  make clean          - rimuove public/, resources/ e .hugo_build.lock"
	@echo "  make publish        - build di produzione + upload via FTP (mirror, cancella i file orfani)"
	@echo "  make publish-dry-run - come publish, ma mostra solo cosa cambierebbe (nessun upload)"

# --- Build -------------------------------------------------------------

build:
	$(HUGO) --gc --minify

build-drafts:
	$(HUGO) --gc --minify -D

build-future:
	$(HUGO) --gc --minify -F

build-all:
	$(HUGO) --gc --minify -D -F

# --- Server locale -------------------------------------------------------

serve:
	$(HUGO) server -D -F

serve-prod:
	$(HUGO) server

# --- Pulizia ---------------------------------------------------------------

clean:
	rm -rf $(BUILD_DIR) resources .hugo_build.lock

# --- Pubblicazione via FTP (Aruba) ------------------------------------------
#
# Usa lftp in modalità "mirror --reverse": carica su $(FTP_REMOTE_DIR) solo i
# file nuovi/modificati di $(BUILD_DIR) e CANCELLA sul server quelli non più
# presenti in locale (--delete). È un'operazione che modifica il sito live:
# usa prima "make publish-dry-run" per vedere cosa cambierebbe.
#
# ftp:ssl-protect-data no: l'hosting Aruba tronca silenziosamente ogni file
# più grande di 16384 byte (un singolo record TLS) quando il canale dati è
# cifrato — bug lato server/proxy Aruba, riprodotto e isolato il 16/08/2026
# (confermato via "quote SIZE" sul file appena caricato, non solo lato HTTP:
# il file sul server risultava davvero troncato). "226 Transfer complete"
# arriva comunque dal server, quindi lftp non segnala alcun errore: il
# troncamento passa inosservato finché non si controlla a mano. Disattivare
# la cifratura del solo canale dati (il canale di controllo resta protetto)
# risolve: verificato byte-per-byte con un file di test. Accettabile qui
# perché il contenuto pubblicato è comunque pubblico (nessun dato sensibile
# transita in chiaro). Senza questa opzione NON rimuovere --delete/mirror
# senza prima rifare un controllo dimensioni: i file già troncati sul server
# vengono ri-caricati correttamente al prossimo "make publish" solo perché
# mirror confronta le dimensioni e nota la discrepanza.

check-ftp-vars:
	@if [ -z "$(FTP_HOST)" ] || [ -z "$(FTP_USER)" ] || [ -z "$(FTP_PASS)" ]; then \
		echo "Mancano le credenziali FTP."; \
		echo "Crea un file .env.ftp (vedi .env.ftp.example) con FTP_HOST, FTP_USER, FTP_PASS"; \
		echo "e opzionalmente FTP_REMOTE_DIR (default ftps, obbligatorio per questo hosting)."; \
		exit 1; \
	fi
	@command -v lftp >/dev/null 2>&1 || { \
		echo "lftp non è installato. Su Debian/Ubuntu: sudo apt-get install -y lftp"; \
		exit 1; \
	}

publish-dry-run: check-ftp-vars build
	lftp -u "$(FTP_USER),$(FTP_PASS)" $(FTP_PROTOCOL)://$(FTP_HOST) -e "\
		set ftp:passive-mode true; \
		set ssl:verify-certificate off; \
		set ftp:list-options -a; \
		set ftp:ssl-protect-data no; \
		mirror --reverse --delete --verbose --dry-run $(BUILD_DIR) $(FTP_REMOTE_DIR); \
		bye"

# --parallel=3: tradeoff scelto per non saturare le sessioni FTP concorrenti
# consentite dal piano Aruba — il limite reale non è confermato (potrebbe
# essere 4 o diverso), 3 è un valore prudenziale sotto quella soglia ignota.
# Se "mirror" fallisce con errori di troppe connessioni, abbassare qui.
publish: check-ftp-vars build
	lftp -u "$(FTP_USER),$(FTP_PASS)" $(FTP_PROTOCOL)://$(FTP_HOST) -e "\
		set ftp:passive-mode true; \
		set ssl:verify-certificate off; \
		set ftp:list-options -a; \
		set ftp:ssl-protect-data no; \
		mirror --parallel=3 --reverse --delete --verbose $(BUILD_DIR) $(FTP_REMOTE_DIR); \
		bye"
