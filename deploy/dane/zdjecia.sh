#!/bin/bash
# Zdjęcia produktów w img/p. Uruchamiane w kontenerze prestashop przez deploy/scripts/init.sh i zrzut.sh:
#   jest              kod 0, gdy w sklepie są już kompletne zdjęcia z tej wersji danych
#   pobierz           pobiera archiwum z ZDJECIA_URL i rozpakowuje; kod 3, gdy archiwum jest niedostępne
#   uzupelnij [KAT]   tworzy brakujące oryginały (z KAT/results.json) i miniatury, w kilku procesach naraz
#   oznacz            zapisuje, że zdjęcia z tej wersji danych są kompletne
#   archiwum          tworzy /tmp/zdjecia.tar i /tmp/zdjecia.sha256 (make zrzut)
set -euo pipefail

IMG=/var/www/html/img/p
SUMA=/opt/dane/zdjecia.sha256
ZNACZNIK=$IMG/.zdjecia
ARCHIWUM=/tmp/zdjecia.tar
# Limit z wymagań. Gdy pełne img/p jest większe, archiwum pomija największe typy miniatur,
# a make init tworzy je z oryginałów.
LIMIT_BAJTOW=${ZDJECIA_LIMIT_BAJTOW:-1000000000}

oczekiwana_suma() {
    cut -d' ' -f1 "$SUMA" | tr -d '\r\n'
}

jest() {
    [ -f "$ZNACZNIK" ] && [ "$(cat "$ZNACZNIK")" = "$(oczekiwana_suma)" ]
}

oznacz() {
    oczekiwana_suma > "$ZNACZNIK"
    chown www-data:www-data "$ZNACZNIK"
}

# Plik z Releases. Przy prywatnym repozytorium adres ze strony wymaga zalogowania w przeglądarce,
# więc z tokenem pobieramy przez API GitHuba. Token idzie w nagłówku przez stdin (-K -), a nie w argumentach.
pobierz_plik() {
    if [ -z "${GITHUB_TOKEN:-}" ]; then
        curl -fL --retry 3 --connect-timeout 20 --progress-bar -o "$ARCHIWUM" "$ZDJECIA_URL"
        return
    fi

    # ZDJECIA_URL = https://github.com/<właściciel>/<repozytorium>/releases/download/<tag>/<plik>
    local sciezka repo tag nazwa wydanie api
    sciezka=${ZDJECIA_URL#https://github.com/}
    repo=$(echo "$sciezka" | cut -d/ -f1,2)
    tag=$(echo "$sciezka" | cut -d/ -f5)
    nazwa=$(echo "$sciezka" | cut -d/ -f6)

    wydanie=$(printf 'header = "Authorization: Bearer %s"\n' "$GITHUB_TOKEN" \
        | curl -fsSL -K - -H "Accept: application/vnd.github+json" \
            "https://api.github.com/repos/$repo/releases/tags/$tag") || return
    api=$(printf '%s' "$wydanie" | php -r '$r = json_decode(stream_get_contents(STDIN), true);
        foreach ($r["assets"] ?? [] as $a) { if ($a["name"] === $argv[1]) { echo $a["url"]; } }' "$nazwa")

    if [ -z "$api" ]; then
        echo "Nie znaleziono pliku $nazwa w wydaniu $tag repozytorium $repo (sprawdź GITHUB_TOKEN i ZDJECIA_URL)" >&2
        return 1
    fi

    printf 'header = "Authorization: Bearer %s"\n' "$GITHUB_TOKEN" \
        | curl -fL -K - --retry 3 --connect-timeout 20 --progress-bar \
            -H "Accept: application/octet-stream" -o "$ARCHIWUM" "$api"
}

pobierz() {
    if [ -z "${ZDJECIA_URL:-}" ]; then
        echo "Brak ZDJECIA_URL w .env. Skopiuj ten wiersz z .env.example i uruchom make up."
        return 3
    fi

    echo "Pobieram archiwum zdjęć: $ZDJECIA_URL"
    rm -f "$ARCHIWUM"
    local kod=0
    pobierz_plik || kod=$?
    if [ "$kod" -ne 0 ]; then
        rm -f "$ARCHIWUM"
        # 35 i 60: błąd TLS. Zapasowa ścieżka też by nie zadziałała, więc nie ma sensu do niej przechodzić.
        if [ "$kod" -eq 35 ] || [ "$kod" -eq 60 ]; then
            echo "BLAD: połączenie HTTPS odrzucone przez certyfikat. Zwykle to antywirus skanujący HTTPS," >&2
            echo "zobacz README, sekcja Problemy." >&2
            return 1
        fi
        echo "Archiwum zdjęć jest niedostępne."
        return 3
    fi

    local suma
    suma=$(sha256sum "$ARCHIWUM" | cut -d' ' -f1)
    if [ "$suma" != "$(oczekiwana_suma)" ]; then
        rm -f "$ARCHIWUM"
        echo "BLAD: archiwum spod ZDJECIA_URL nie pasuje do zrzutu bazy (inna suma SHA-256 niż w deploy/dane/zdjecia.sha256)." >&2
        echo "Skopiuj aktualny ZDJECIA_URL z .env.example do .env, potem make up i make init." >&2
        return 1
    fi

    echo "Rozpakowuję do img/p..."
    # Katalogi 1-9 to zdjęcia produktów: z danych demo instalatora albo z poprzedniej wersji danych
    find "$IMG" -mindepth 1 -maxdepth 1 -name '[0-9]' -exec rm -rf {} +
    tar -xf "$ARCHIWUM" -C "$IMG" --no-same-owner
    rm -f "$ARCHIWUM"
    chown -R www-data:www-data "$IMG"
    echo "Zdjęcia z archiwum: OK"
}

uzupelnij() {
    local procesy czesc=0 pidy=() kod=0 pid
    procesy=$(nproc)
    echo "Uzupełniam brakujące zdjęcia i miniatury ($procesy procesów)..."
    while [ "$czesc" -lt "$procesy" ]; do
        php /opt/dane/zdjecia.php "$czesc" "$procesy" "$@" &
        pidy+=("$!")
        czesc=$((czesc + 1))
    done
    for pid in "${pidy[@]}"; do
        wait "$pid" || kod=$?
    done
    return "$kod"
}

# Rozmiar w archiwum tar: nagłówek 512 B i treść zaokrąglona w górę do 512 B
rozmiar_w_tar() {
    find "$@" -type f -printf '%s\n' | awk '{ s += 512 + int(($1 + 511) / 512) * 512 } END { printf "%d\n", s }'
}

archiwum() {
    cd "$IMG"
    shopt -s nullglob
    local katalogi=([0-9])
    if [ ${#katalogi[@]} -eq 0 ]; then
        echo "BLAD: w img/p nie ma zdjęć produktów. Najpierw import." >&2
        exit 1
    fi

    local razem typ rozmiar pomin=()
    razem=$(rozmiar_w_tar "${katalogi[@]}")
    echo "Zdjęcia w img/p: $((razem / 1000000)) MB, limit archiwum: $((LIMIT_BAJTOW / 1000000)) MB"

    # Typy miniatur od największego. Pomijamy je po kolei, aż archiwum zmieści się w limicie.
    while read -r rozmiar typ; do
        [ "$razem" -le "$LIMIT_BAJTOW" ] && break
        pomin+=("--exclude=*-$typ.jpg")
        razem=$((razem - rozmiar))
        echo "Pomijam miniatury $typ ($((rozmiar / 1000000)) MB), make init utworzy je z oryginałów"
    done < <(
        php -r 'require "/var/www/html/config/config.inc.php";
            foreach (ImageType::getImagesTypes("products") as $t) { echo $t["name"], "\n"; }' \
        | while read -r typ; do
            echo "$(rozmiar_w_tar "${katalogi[@]}" -name "*-$typ.jpg") $typ"
        done | sort -rn
    )

    if [ "$razem" -gt "$LIMIT_BAJTOW" ]; then
        echo "BLAD: same oryginały przekraczają limit archiwum" >&2
        exit 1
    fi

    rm -f "$ARCHIWUM"
    tar -cf "$ARCHIWUM" --owner=0 --group=0 --numeric-owner "${pomin[@]}" "${katalogi[@]}"
    (cd /tmp && sha256sum "$(basename "$ARCHIWUM")" > /tmp/zdjecia.sha256)
    echo "Archiwum zdjęć: $(du -h "$ARCHIWUM" | cut -f1), $(tar -tf "$ARCHIWUM" | grep -c '\.jpg$') plików JPG"
}

case "${1:-}" in
    jest) jest ;;
    pobierz) pobierz ;;
    uzupelnij) shift; uzupelnij "$@" ;;
    oznacz) oznacz ;;
    archiwum) archiwum ;;
    *) echo "Użycie: $0 jest|pobierz|uzupelnij [katalog]|oznacz|archiwum" >&2; exit 2 ;;
esac
