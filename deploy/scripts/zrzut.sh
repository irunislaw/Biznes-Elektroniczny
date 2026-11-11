#!/bin/sh
# make zrzut: zapisuje dane sklepu po imporcie, żeby make init odtworzył je u innych bez importu.
#  - deploy/dane/sklep.sql.gz   baza bez kluczy Webservice, klientów, adresów, zamówień, koszyków i logów (do repozytorium),
#  - deploy/dane/zdjecia.tar    zdjęcia produktów z img/p (do GitHub Releases, nie do repozytorium),
#  - deploy/dane/zdjecia.sha256 suma archiwum, którą make init sprawdza po pobraniu (do repozytorium).
set -eu
export MSYS_NO_PATHCONV=1

COMPOSE=${COMPOSE:-docker compose --env-file .env -f deploy/compose.yaml}
DANE=deploy/dane
# Limit archiwum zdjęć z wymagań: 1 GB. Gdy img/p jest większe, archiwum pomija największe typy miniatur.
ZDJECIA_LIMIT_BAJTOW=${ZDJECIA_LIMIT_BAJTOW:-1000000000}

$COMPOSE exec -T db bash /opt/dane/baza.sh zrzut
$COMPOSE cp db:/tmp/sklep.sql.gz "$DANE/sklep.sql.gz"
$COMPOSE exec -T db rm -f /tmp/sklep.sql.gz

$COMPOSE exec -T -e ZDJECIA_LIMIT_BAJTOW="$ZDJECIA_LIMIT_BAJTOW" prestashop bash /opt/dane/zdjecia.sh archiwum
$COMPOSE cp prestashop:/tmp/zdjecia.tar "$DANE/zdjecia.tar"
$COMPOSE cp prestashop:/tmp/zdjecia.sha256 "$DANE/zdjecia.sha256"
$COMPOSE exec -T prestashop rm -f /tmp/zdjecia.tar /tmp/zdjecia.sha256

# Ten sklep ma już te dane, więc make init nie wczyta ich tu ponownie
$COMPOSE exec -T db bash /opt/dane/baza.sh oznacz
$COMPOSE exec -T prestashop bash /opt/dane/zdjecia.sh oznacz

echo
ls -l "$DANE/sklep.sql.gz" "$DANE/zdjecia.tar" "$DANE/zdjecia.sha256"
cat <<'KONIEC'

Dalej:
  1. Commit deploy/dane/sklep.sql.gz i deploy/dane/zdjecia.sha256.
  2. Na GitHubie: Releases -> Create a new release, nowy tag (np. dane-v2), załącz deploy/dane/zdjecia.tar.
  3. Jeśli tag się zmienił, popraw ZDJECIA_URL w .env.example (i we własnym .env).
KONIEC
