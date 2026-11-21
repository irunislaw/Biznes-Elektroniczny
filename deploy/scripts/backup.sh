#!/bin/sh
# make backup: kopia działającego sklepu w backups/sklep-<data>_<godzina>.tar. W archiwum:
#   kopia.txt                    opis: data, wersja PrestaShop, domena, liczba produktów, zdjęć, klientów i zamówień,
#   baza.sql.gz                  pełny zrzut bazy, razem z klientami, zamówieniami, kontami i kluczami Webservice,
#   img/, modules/ps_banner/img/ zdjęcia sklepu,
#   app/config/parameters.php, .htaccess, config/themes/   pliki konfiguracyjne sklepu.
# Archiwum ma dane osobowe, hasła i klucze, dlatego backups/ jest w .gitignore. Opis: docs/backup.md.
set -eu
# shellcheck source=deploy/scripts/wspolne.sh
. deploy/scripts/wspolne.sh

KATALOG=backups
plik=$KATALOG/sklep-$(date +%Y-%m-%d_%H%M%S).tar

# Na Linuksie i macOS kopię może czytać tylko jej właściciel
umask 077
mkdir -p "$KATALOG"

# Także po błędzie: bez niepełnego archiwum i bez kopii bazy w kontenerach
sprzataj() {
    rm -f "$plik.tmp" "$plik.sql.gz"
    sklep bash /opt/dane/kopia.sh sprzataj 2>/dev/null || true
    baza rm -f /tmp/kopia.sql.gz 2>/dev/null || true
}
trap sprzataj EXIT

krok "1/3 Sklep"
czekaj_na_sklep
sklep bash /opt/dane/kopia.sh przygotuj

krok "2/3 Baza danych"
baza bash /opt/dane/baza.sh kopia
# Z kontenera bazy do kontenera sklepu, który składa archiwum
$COMPOSE cp db:/tmp/kopia.sql.gz "$plik.sql.gz"
$COMPOSE cp "$plik.sql.gz" prestashop:/var/www/html/var/kopia/baza.sql.gz

krok "3/3 Zdjęcia, pliki konfiguracyjne i archiwum"
sklep bash /opt/dane/kopia.sh archiwum > "$plik.tmp"
mv "$plik.tmp" "$plik"

printf '\nGotowe w %s s. Kopia: %s (%s)\n' "$(($(date +%s) - start))" "$plik" "$(du -h "$plik" | cut -f1)"
cat <<KONIEC
Archiwum ma dane osobowe klientów, hasła i klucze sklepu: nie dodawaj go do repozytorium i nie wysyłaj.
Odtworzenie na czystym środowisku: make reset, make up, make restore PLIK=$plik
KONIEC
