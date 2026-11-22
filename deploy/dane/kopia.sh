#!/bin/bash
# Pliki sklepu w kopii zapasowej. Uruchamiane w kontenerze prestashop przez deploy/scripts/backup.sh i restore.sh:
#   przygotuj  zakłada katalog roboczy i zapisuje w nim opis kopii (kopia.txt)            (make backup)
#   archiwum   wypisuje na standardowe wyjście archiwum: opis, zrzut bazy z katalogu roboczego,
#              zdjęcia i pliki konfiguracyjne                                             (make backup)
#   rozpakuj   rozpakowuje archiwum ze standardowego wejścia do katalogu roboczego
#              i sprawdza, czy jest z tej samej wersji PrestaShop                         (make restore)
#   sprawdz    porównuje liczbę produktów, zdjęć, klientów i zamówień w bazie z kopią     (make restore)
#   odtworz    zastępuje zdjęcia i pliki konfiguracyjne sklepu tymi z kopii               (make restore)
#   sprzataj   usuwa katalog roboczy
set -euo pipefail

cd /var/www/html

# W wolumenie sklepu, więc zdjęcia przenosimy do img/ bez kopiowania. var/ jest zamknięty dla przeglądarki
# (var/.htaccess), więc zrzutu bazy i parameters.php z kopii nie da się pobrać ze sklepu.
ROBOCZY=/var/www/html/var/kopia

# Zdjęcia: img/ (produkty, kategorie, logo) i baner strony głównej, który ps_banner trzyma w swoim katalogu
ZDJECIA="img modules/ps_banner/img"
# Pliki konfiguracyjne. .htaccess i ustawienia motywu przechodzą z kopii w całości,
# a parameters.php tylko częściowo (kopia.php parametry).
KONFIGURACJA=".htaccess config/themes"
PARAMETRY=app/config/parameters.php

# PHP jako www-data: pliki cache utworzone przez roota psułyby działający sklep (błąd 500)
php_www() { runuser -u www-data -- php /opt/dane/kopia.php "$@"; }

sprzataj() {
    rm -rf "$ROBOCZY"
}

przygotuj() {
    sprzataj
    mkdir -p "$ROBOCZY"
    php_www opis > "$ROBOCZY/kopia.txt"
}

archiwum() {
    # shellcheck disable=SC2086  # listy ścieżek bez spacji
    tar -c -f - -C "$ROBOCZY" kopia.txt baza.sql.gz -C /var/www/html $PARAMETRY $KONFIGURACJA $ZDJECIA
}

rozpakuj() {
    local sciezka
    sprzataj
    mkdir -p "$ROBOCZY"
    echo "Rozpakowuję kopię..."
    tar -x -f - -C "$ROBOCZY"
    for sciezka in kopia.txt baza.sql.gz $PARAMETRY $KONFIGURACJA $ZDJECIA; do
        if [ ! -e "$ROBOCZY/$sciezka" ]; then
            echo "BLAD: w kopii nie ma $sciezka. Czy to archiwum z make backup?" >&2
            exit 1
        fi
    done
    php_www wersja "$ROBOCZY/kopia.txt"
}

sprawdz() {
    php_www sprawdz "$ROBOCZY/kopia.txt"
}

odtworz() {
    local sciezka
    # Całe katalogi zamiast dopisywania, więc nie zostają zdjęcia demo ze świeżej instalacji
    for sciezka in $ZDJECIA $KONFIGURACJA; do
        rm -rf "$sciezka"
        mv "$ROBOCZY/$sciezka" "$sciezka"
    done
    echo "Zdjęcia: OK ($(find img -name '*.jpg' | wc -l) plików JPG w img/)"

    php_www parametry "$ROBOCZY/$PARAMETRY"
    # Cache Symfony ma w sobie parametry i stan bazy sprzed odtworzenia
    rm -rf var/cache/prod var/cache/dev
    echo "Pliki konfiguracyjne: OK"
}

case "${1:-}" in
    przygotuj) przygotuj ;;
    archiwum) archiwum ;;
    rozpakuj) rozpakuj ;;
    sprawdz) sprawdz ;;
    odtworz) odtworz ;;
    sprzataj) sprzataj ;;
    *) echo "Użycie: $0 przygotuj|archiwum|rozpakuj|sprawdz|odtworz|sprzataj" >&2; exit 2 ;;
esac
