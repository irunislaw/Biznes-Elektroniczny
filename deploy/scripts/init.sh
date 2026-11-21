#!/bin/sh
# make init: dane i konfiguracja sklepu po make up.
#  1. czeka, aż instalator PrestaShop skończy pracę, i kopiuje moduł z shop/modules/ i motyw z shop/themes/,
#  2. wczytuje zrzut bazy deploy/dane/sklep.sql.gz,
#  3. pobiera archiwum zdjęć z Releases (ZDJECIA_URL), a gdy jest niedostępne, zdjęcia z adresów
#     w scraper-results/results.json; potem tworzy brakujące miniatury,
#  4. ustawia domenę, SSL i konto administratora z .env,
#  5. uruchamia skrypty konfiguracji z deploy/config/ (w tym włączenie motywu) i czyści cache.
# Drugie uruchomienie niczego nie psuje: zrzut i zdjęcia wczytują się tylko wtedy, gdy w sklepie
# jest inna wersja danych, a skrypty konfiguracji zmieniają tylko to, co się różni.
# make init DANE=0 pomija kroki 2 i 3 (sklep zostaje z danymi demo), np. przed nowym importem.
set -eu
# shellcheck source=deploy/scripts/wspolne.sh
. deploy/scripts/wspolne.sh

PYTHON_IMAGE=python:3.13-slim
DANE=${DANE:-1}

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

krok "1/5 Instalacja sklepu, moduł i motyw z repozytorium"
czekaj_na_sklep
# Przed wczytaniem zrzutu: gdy zrzut ma włączony motyw gitara, PrestaShop bez jego plików się nie uruchamia,
# a krok 3 (zdjecia.php) już z niego korzysta
kopiuj_modul_i_motyw

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
# Świeża kopia modułów z repozytorium przy każdym make init.
for modul in becookiebanner beomnibus; do
    sklep rm -rf "/var/www/html/modules/$modul"
    $COMPOSE cp "shop/modules/$modul" "prestashop:/var/www/html/modules/$modul"
    sklep chown -R www-data:www-data "/var/www/html/modules/$modul"
done
# To samo dla motywu potomnego. Włącza go theme.php, pierwszy w pętli, bo przy przełączaniu motywu
# PrestaShop zapisuje od nowa hooki i typy miniatur, a kolejne skrypty mają działać na stanie końcowym.
sklep rm -rf /var/www/html/themes/gitara
$COMPOSE cp shop/themes/gitara prestashop:/var/www/html/themes/gitara
sklep chown -R www-data:www-data /var/www/html/themes/gitara
for skrypt in theme locale taxes payments carriers mail cookies omnibus cms uklad; do
    sklep php "/opt/prestashop-config/$skrypt.php"
done
szablony_maili
sklep php /opt/import/init_webservice.php
wyczysc_cache
gotowe
