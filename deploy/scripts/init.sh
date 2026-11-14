#!/bin/sh
# make init: dane i konfiguracja sklepu po make up.
#  1. czeka, aż instalator PrestaShop skończy pracę,
#  2. wczytuje zrzut bazy deploy/dane/sklep.sql.gz,
#  3. pobiera archiwum zdjęć z Releases (ZDJECIA_URL), a gdy jest niedostępne, zdjęcia z adresów
#     w scraper-results/results.json; potem tworzy brakujące miniatury,
#  4. ustawia domenę, SSL i konto administratora z .env,
#  5. uruchamia skrypty konfiguracji z deploy/config/ i czyści cache.
# Drugie uruchomienie niczego nie psuje: zrzut i zdjęcia wczytują się tylko wtedy, gdy w sklepie
# jest inna wersja danych, a skrypty konfiguracji zmieniają tylko to, co się różni.
# make init DANE=0 pomija kroki 2 i 3 (sklep zostaje z danymi demo), np. przed nowym importem.
set -eu
export MSYS_NO_PATHCONV=1

COMPOSE=${COMPOSE:-docker compose --env-file .env -f deploy/compose.yaml}
PYTHON_IMAGE=python:3.13-slim
DANE=${DANE:-1}

start=$(date +%s)

krok() {
    printf '\n== %s (%ss)\n' "$1" "$(($(date +%s) - start))"
}

sklep() { $COMPOSE exec -T prestashop "$@"; }
sklep_www() { $COMPOSE exec -T -u www-data prestashop "$@"; }
baza() { $COMPOSE exec -T db "$@"; }

# Zapasowa ścieżka: zdjęcia z adresów zapisanych przez scraper, z tym samym limitem zapytań, User-Agentem
# i skalowaniem co przy scrapowaniu. Pliki, które już są w scraper-results/images/, nie są pobierane drugi raz.
pobierz_ze_sklepu_zrodlowego() {
    # Git Bash: Docker potrzebuje ścieżki C:/..., a nie /c/...
    katalog=$(pwd -W 2>/dev/null || pwd)
    uzytkownik=
    if [ "$(uname -s)" = Linux ]; then
        uzytkownik="--user $(id -u):$(id -g)"
    fi
    # shellcheck disable=SC2086
    if ! docker run --rm $uzytkownik -e HOME=/tmp -v "$katalog:/work" -w /work/scraper "$PYTHON_IMAGE" sh -c '
        pip install --quiet --disable-pip-version-check --root-user-action=ignore --target /tmp/pakiety -r requirements.txt \
        && PYTHONPATH=/tmp/pakiety python download_images.py --bez-zapisu'; then
        echo "BLAD: pobieranie zdjęć się nie powiodło. Przy CERTIFICATE_VERIFY_FAILED zobacz README, sekcja Problemy." >&2
        exit 1
    fi
}

krok "1/5 Instalacja sklepu"
if ! $COMPOSE ps --status running --services | grep -qx prestashop; then
    echo "BLAD: kontener prestashop nie działa. Najpierw make up." >&2
    exit 1
fi
czekam=0
until sklep sh -c 'test -f app/config/parameters.php && test ! -f install.lock' 2>/dev/null; do
    if [ "$czekam" -eq 0 ]; then
        echo "Czekam, aż instalator PrestaShop skończy pracę (postęp: make logs)..."
    fi
    if [ "$czekam" -ge 900 ]; then
        echo "BLAD: instalacja trwa ponad 15 min. Sprawdź make logs." >&2
        exit 1
    fi
    sleep 5
    czekam=$((czekam + 5))
done
if sklep sh -c 'test -d "$PS_FOLDER_INSTALL"'; then
    echo "BLAD: instalacja PrestaShop się nie powiodła. Zobacz sekcję Problemy w README." >&2
    exit 1
fi
echo "Sklep zainstalowany"

krok "2/5 Baza danych"
if [ "$DANE" = 0 ]; then
    echo "Pominięte (DANE=0): sklep zostaje z danymi demo instalatora"
else
    baza bash /opt/dane/baza.sh wczytaj
fi

krok "3/5 Zdjęcia produktów"
if [ "$DANE" = 0 ]; then
    echo "Pominięte (DANE=0)"
elif sklep bash /opt/dane/zdjecia.sh jest; then
    echo "Zdjęcia z tej wersji danych są już w sklepie"
else
    zrodlo=
    if sklep bash /opt/dane/zdjecia.sh pobierz; then
        :
    else
        kod=$?
        if [ "$kod" -ne 3 ]; then
            exit "$kod"
        fi
        echo "Pobieram zdjęcia z adresów w scraper-results/results.json (2 zdjęcia/s, pełny zbiór to ok. 1 h)..."
        pobierz_ze_sklepu_zrodlowego
        zrodlo=/opt/scraper-results
    fi
    if sklep_www bash /opt/dane/zdjecia.sh uzupelnij $zrodlo; then
        sklep bash /opt/dane/zdjecia.sh oznacz
        echo "Zdjęcia: OK"
    else
        echo "UWAGA: części zdjęć brakuje (lista wyżej). Następne make init spróbuje je uzupełnić." >&2
    fi
fi

krok "4/5 Domena, SSL i administrator z .env"
sklep php /opt/dane/dopasuj.php

krok "5/5 Konfiguracja sklepu (deploy/config) i cache"
for skrypt in locale taxes payments carriers mail cms; do
    sklep php "/opt/prestashop-config/$skrypt.php"
done
sklep php bin/console prestashop:mail:generate modern pl-PL /var/www/html/mails /var/www/html/modules --overwrite=1
sklep_www mkdir -p /var/www/html/themes/classic/mails
sklep php bin/console prestashop:mail:generate modern pl-PL /var/www/html/themes/classic/mails \
    /var/www/html/themes/classic/modules --overwrite=1
sklep php /opt/import/init_webservice.php
# Skrypty działały jako root, więc cache tworzymy od nowa jako www-data.
# img/tmp to miniatury z panelu, które mogły zostać po produktach demo.
sklep sh -c 'rm -rf var/cache/prod var/cache/dev \
    && mkdir -p var/cache/prod/purifier \
    && chown -R www-data:www-data var/cache \
    && find img/tmp -name "*.jpg" -delete'
echo "Cache: OK"

domena=$(sklep printenv PS_DOMAIN | tr -d '\r')
printf '\nGotowe w %s s. Sklep: https://%s\n' "$(($(date +%s) - start))" "$domena"
