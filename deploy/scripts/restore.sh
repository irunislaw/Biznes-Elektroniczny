#!/bin/sh
# make restore PLIK=backups/sklep-<data>_<godzina>.tar: sklep z kopii (make backup) na czystym środowisku po make up.
#  1. czeka, aż instalator PrestaShop skończy pracę, i kopiuje moduł i motyw z repozytorium,
#  2. rozpakowuje kopię w kontenerze sklepu i sprawdza, czy jest z tej samej wersji PrestaShop,
#  3. zastępuje bazę zrzutem z kopii i porównuje liczbę produktów, zdjęć, klientów i zamówień z opisem kopii,
#  4. zastępuje zdjęcia i pliki konfiguracyjne tymi z kopii (z parameters.php tylko klucze sklepu),
#  5. ustawia domenę i SSL z .env,
#  6. generuje szablony e-maili i czyści cache.
# Konto administratora, klucze Webservice i ustawienia sklepu zostają takie, jak w kopii. Opis: docs/backup.md.
set -eu
# shellcheck source=deploy/scripts/wspolne.sh
. deploy/scripts/wspolne.sh

PLIK=${PLIK:-}

if [ -z "$PLIK" ]; then
    echo "Użycie: make restore PLIK=backups/sklep-<data>_<godzina>.tar" >&2
    if ls backups/*.tar >/dev/null 2>&1; then
        echo "Kopie w backups/:" >&2
        ls -1 backups/*.tar >&2
    fi
    exit 2
fi

if [ ! -f "$PLIK" ]; then
    echo "BLAD: nie ma pliku $PLIK" >&2
    exit 1
fi

trap 'sklep bash /opt/dane/kopia.sh sprzataj 2>/dev/null || true' EXIT

krok "1/6 Instalacja sklepu, moduł i motyw z repozytorium"
czekaj_na_sklep
# Przed wczytaniem bazy: baza z kopii ma włączony motyw gitara, a bez jego plików PrestaShop się nie uruchomi
kopiuj_modul_i_motyw

krok "2/6 Kopia $PLIK"
sklep bash /opt/dane/kopia.sh rozpakuj < "$PLIK"

krok "3/6 Baza danych"
sklep cat /var/www/html/var/kopia/baza.sql.gz | baza bash /opt/dane/baza.sh odtworz
sklep bash /opt/dane/kopia.sh sprawdz

krok "4/6 Zdjęcia i pliki konfiguracyjne"
sklep bash /opt/dane/kopia.sh odtworz

krok "5/6 Domena i SSL z .env"
sklep php /opt/dane/dopasuj.php domena

krok "6/6 Szablony e-maili i cache"
szablony_maili
wyczysc_cache
gotowe
