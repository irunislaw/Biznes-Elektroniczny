#!/bin/sh
# Wspólne części skryptów uruchamianych na komputerze: make init (init.sh), make backup (backup.sh)
# i make restore (restore.sh). Wczytywane przez ". deploy/scripts/wspolne.sh" z katalogu głównego repozytorium.
# shellcheck disable=SC2034  # start i COMPOSE są używane w skryptach, które wczytują ten plik

export MSYS_NO_PATHCONV=1

COMPOSE=${COMPOSE:-docker compose --env-file .env -f deploy/compose.yaml}

start=$(date +%s)

krok() {
    printf '\n== %s (%ss)\n' "$1" "$(($(date +%s) - start))"
}

sklep() { $COMPOSE exec -T prestashop "$@"; }
sklep_www() { $COMPOSE exec -T -u www-data prestashop "$@"; }
baza() { $COMPOSE exec -T db "$@"; }

# Czeka, aż instalator PrestaShop skończy pracę po make up.
czekaj_na_sklep() {
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
    # shellcheck disable=SC2016  # zmienna z kontenera, nie z komputera
    if sklep sh -c 'test -d "$PS_FOLDER_INSTALL"'; then
        echo "BLAD: instalacja PrestaShop się nie powiodła. Zobacz sekcję Problemy w README." >&2
        exit 1
    fi
    echo "Sklep zainstalowany"
}

# Świeża kopia modułu i motywu z repozytorium (shop/). Baza wskazuje na nie, a po make reset
# w wolumenie sklepu ich nie ma.
kopiuj_modul_i_motyw() {
    sklep rm -rf /var/www/html/modules/becookiebanner
    $COMPOSE cp shop/modules/becookiebanner prestashop:/var/www/html/modules/becookiebanner
    sklep chown -R www-data:www-data /var/www/html/modules/becookiebanner
    sklep rm -rf /var/www/html/themes/gitara
    $COMPOSE cp shop/themes/gitara prestashop:/var/www/html/themes/gitara
    sklep chown -R www-data:www-data /var/www/html/themes/gitara
}

# Polskie szablony e-maili. Instalator zostawia angielskie.
szablony_maili() {
    sklep php bin/console prestashop:mail:generate modern pl-PL /var/www/html/mails /var/www/html/modules --overwrite=1
    sklep_www mkdir -p /var/www/html/themes/classic/mails
    sklep php bin/console prestashop:mail:generate modern pl-PL /var/www/html/themes/classic/mails \
        /var/www/html/themes/classic/modules --overwrite=1
}

# Skrypty PHP działały jako root, więc cache tworzymy od nowa jako www-data.
# img/tmp to miniatury z panelu, które mogły zostać po produktach demo.
wyczysc_cache() {
    sklep sh -c 'rm -rf var/cache/prod var/cache/dev \
        && mkdir -p var/cache/prod/purifier \
        && chown -R www-data:www-data var/cache \
        && find img/tmp -name "*.jpg" -delete'
    echo "Cache: OK"
}

gotowe() {
    domena=$(sklep printenv PS_DOMAIN | tr -d '\r')
    printf '\nGotowe w %s s. Sklep: https://%s\n' "$(($(date +%s) - start))" "$domena"
}
