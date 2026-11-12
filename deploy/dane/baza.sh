#!/bin/bash
# Baza sklepu. Uruchamiane w kontenerze db przez deploy/scripts/init.sh i deploy/scripts/zrzut.sh:
#   wczytaj  wczytuje /opt/dane/sklep.sql.gz, jeśli w bazie nie ma jeszcze tej wersji zrzutu
#   zrzut    zapisuje bazę bez sekretów i danych osobowych do /tmp/sklep.sql.gz (make zrzut)
#   oznacz   zapisuje w bazie, że jest w niej wersja danych z /opt/dane/sklep.sql.gz
set -euo pipefail

ZRZUT=/opt/dane/sklep.sql.gz
# Suma SHA-256 wczytanego zrzutu. Dzięki niej drugie make init nie nadpisuje bazy (np. kont z testów),
# a po zmianie sklep.sql.gz w repozytorium wczytuje nową wersję.
ZNACZNIK=PROJEKT_ZRZUT_SHA256
# Ten adres zrzut wpisuje zamiast e-maila administratora, a make init (dopasuj.php) zamienia go na ADMIN_MAIL
ZASLEPKA_EMAIL=admin@example.com

# Tabele zapisywane bez danych (zostaje sama struktura):
BEZ_DANYCH="
    webservice_account webservice_account_shop webservice_permission
    employee_session customer_session
    customer_message customer_message_sync_imap customer_thread guest
    emailsubscription mailalert_customer_oos psgdpr_log
    wishlist wishlist_product wishlist_product_cart
    product_comment product_comment_grade product_comment_report product_comment_usefulness
    cart cart_product cart_cart_rule customization customized_data
    orders order_detail order_detail_tax order_history order_carrier order_cart_rule
    order_invoice order_invoice_payment order_invoice_tax order_payment
    order_return order_return_detail order_slip order_slip_detail
    message message_readed stock_mvt
    log mail connections connections_page connections_source pagenotfound referrer_cache
    page_viewed date_range statssearch
    smarty_cache smarty_lazy_cache smarty_last_flush layered_filter_block
"
# Pierwsza grupa to klucze Webservice. Klucz API w repozytorium to 0 pkt za W1.
# Potem sesje, dane klientów, koszyki, zamówienia, logi, statystyki odwiedzin i pamięć podręczna.
# Klientów, adresy i administratora czyści SQL w zrzut(), bo części wierszy trzeba w nich zostawić.

export MYSQL_PWD="$MARIADB_ROOT_PASSWORD"
sql() { mariadb -uroot "$@"; }

suma_zrzutu() {
    sha256sum "$ZRZUT" | cut -d' ' -f1
}

oznacz() {
    local suma=${1:-$(suma_zrzutu)}
    sql "$MARIADB_DATABASE" -e "
        DELETE FROM ps_configuration WHERE name = '$ZNACZNIK';
        INSERT INTO ps_configuration (name, value, date_add, date_upd) VALUES ('$ZNACZNIK', '$suma', NOW(), NOW());"
}

wczytaj() {
    local suma wczytana
    suma=$(suma_zrzutu)
    wczytana=$(sql -N "$MARIADB_DATABASE" -e "SELECT value FROM ps_configuration WHERE name = '$ZNACZNIK'" 2>/dev/null || true)

    if [ "$wczytana" = "$suma" ]; then
        echo "Baza: ta wersja zrzutu jest już wczytana"
        return
    fi

    echo "Baza: wczytuję zrzut $(basename "$ZRZUT") ($(du -h "$ZRZUT" | cut -f1))..."
    gunzip -t "$ZRZUT"
    gunzip -c "$ZRZUT" | sql "$MARIADB_DATABASE"
    oznacz "$suma"
    echo "Baza: OK"
}

zrzut() {
    local zrodlo=$MARIADB_DATABASE tymczasowa=zrzut_tmp wyjscie=/tmp/sklep.sql.gz wzorce=/tmp/zrzut_wzorce
    local pomin=() tabela

    for tabela in $BEZ_DANYCH; do
        pomin+=("--ignore-table-data=$zrodlo.ps_$tabela")
    done

    # Kopia w osobnej bazie, żeby wyczyścić dane bez ruszania działającego sklepu
    echo "Zrzut bazy: kopiuję $zrodlo do tymczasowej bazy $tymczasowa..."
    sql -e "DROP DATABASE IF EXISTS $tymczasowa; CREATE DATABASE $tymczasowa"
    mariadb-dump -uroot --single-transaction "${pomin[@]}" "$zrodlo" | sql "$tymczasowa"

    sql "$tymczasowa" <<SQL
-- Administrator: zostaje pierwszy superadministrator, bez e-maila, hasła i imienia autora zrzutu.
-- make init (deploy/dane/dopasuj.php) ustawia e-mail i hasło z ADMIN_MAIL i ADMIN_PASSWORD.
SET @admin = (SELECT MIN(id_employee) FROM ps_employee WHERE id_profile = 1);
DELETE FROM ps_employee WHERE id_employee <> @admin;
DELETE FROM ps_employee_shop WHERE id_employee <> @admin;
UPDATE ps_employee SET
    email = '$ZASLEPKA_EMAIL', passwd = '', firstname = 'Admin', lastname = 'Sklepu',
    last_connection_date = NULL, reset_password_token = NULL, reset_password_validity = NULL,
    id_last_order = 0, id_last_customer_message = 0, id_last_customer = 0, optin = 0
WHERE id_employee = @admin;

-- Klienci i ich adresy. Zostaje tylko klient "Anonymous" modułu psgdpr, któremu moduł przypisuje
-- zamówienia usuniętych klientów. Adresy producentów i dostawców (id_customer = 0) nie są danymi osobowymi.
SET @anonim = IFNULL((SELECT value FROM ps_configuration WHERE name = 'PSGDPR_ANONYMOUS_CUSTOMER'), 0);
SET @anonim_adres = IFNULL((SELECT value FROM ps_configuration WHERE name = 'PSGDPR_ANONYMOUS_ADDRESS'), 0);
DELETE FROM ps_customer WHERE id_customer <> @anonim;
DELETE FROM ps_customer_group WHERE id_customer <> @anonim;
DELETE FROM ps_address WHERE id_customer <> 0 AND id_address <> @anonim_adres;

-- Instalator wpisuje e-mail administratora także tu. make init ustawia je z ADMIN_MAIL.
UPDATE ps_configuration SET value = '$ZASLEPKA_EMAIL'
WHERE name IN ('PS_SHOP_EMAIL', 'PS_LOGS_EMAIL_RECEIVERS', 'MA_MERCHANT_MAILS');
UPDATE ps_contact SET email = '$ZASLEPKA_EMAIL';

-- Sól tokenów i losowa część nazwy eksportu modułu newslettera. make init losuje nowe.
UPDATE ps_configuration SET value = '' WHERE name IN ('NW_SALT', 'PS_NEWSLETTER_RAND');
DELETE FROM ps_configuration WHERE name = '$ZNACZNIK';
SQL

    echo "Zrzut bazy: zapisuję $wyjscie..."
    mariadb-dump -uroot --single-transaction --skip-dump-date "$tymczasowa" | gzip -9n > "$wyjscie"
    sql -e "DROP DATABASE $tymczasowa"

    # Kontrola: w zrzucie nie może być żadnego klucza Webservice ani e-maila pracownika lub klienta ze sklepu.
    # Pomijamy zaślepkę i adresy z danych demo PrestaShop (@prestashop.com, @psgdpr.com).
    sql -N "$zrodlo" -e "
        SELECT \`key\` FROM ps_webservice_account
        UNION SELECT email FROM ps_employee
        UNION SELECT email FROM ps_customer
            WHERE email NOT LIKE '%@prestashop.com' AND email NOT LIKE '%@psgdpr.com'" \
        | grep -vx -e '' -e "$ZASLEPKA_EMAIL" > "$wzorce" || true

    # grep -c czyta całe wejście (-q kończy wcześniej, a wtedy pipefail zgłasza błąd gunzip zamiast trafienia)
    local trafienia
    trafienia=$(gunzip -c "$wyjscie" | grep -ciF -f "$wzorce" || true)
    if [ "$trafienia" != 0 ]; then
        rm -f "$wyjscie" "$wzorce"
        echo "BLAD: w zrzucie został klucz Webservice albo e-mail ze sklepu. Zrzut usunięty." >&2
        exit 1
    fi
    echo "Zrzut bazy: OK (sprawdzono $(wc -l < "$wzorce") kluczy i e-maili, żadnego nie ma w zrzucie)"
    rm -f "$wzorce"
}

case "${1:-}" in
    wczytaj) wczytaj ;;
    zrzut) zrzut ;;
    oznacz) oznacz ;;
    *) echo "Użycie: $0 wczytaj|zrzut|oznacz" >&2; exit 2 ;;
esac
