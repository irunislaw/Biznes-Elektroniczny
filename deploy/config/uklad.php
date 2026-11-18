<?php

// Układ nagłówka, strony głównej i listy produktów jak w sklepie źródłowym (BE-33, docs/wyglad/roznice.md).
// Tylko ustawienia modułów i konfiguracji. Zmiany wyglądu są w shop/themes/gitara/assets/css/custom.css.
// Przy drugim uruchomieniu niczego nie zmienia.

require_once '/var/www/html/config/config.inc.php';

// Moduł menu dołącza klasę Ps_MenuTopLinks zwykłym require, więc nie wczytujemy jej osobno
// (drugie wczytanie kończy się błędem „Cannot declare class”).
$menu = Module::getInstanceByName('ps_mainmenu');
if (!$menu) {
    throw new RuntimeException('Brak modulu ps_mainmenu');
}

$context = Context::getContext();
$idShop = (int) $context->shop->id;
$db = Db::getInstance();

function ustaw(string $klucz, $wartosc): void
{
    if ((string) Configuration::get($klucz) === (string) $wartosc) {
        return;
    }
    if (!Configuration::updateValue($klucz, $wartosc)) {
        throw new RuntimeException("Nie udalo sie ustawic $klucz");
    }
}

// N1: w menu górnym jedna pozycja „Katalog produktów” prowadząca do kategorii głównej, jak w źródle.
// Wyszukiwarka mieści się wtedy w tym samym wierszu bez zmian w CSS. Uwaga: import (deploy/import/import.py,
// setup_ps_main_menu) wpisuje do menu kategorie główne, więc po ponownym imporcie trzeba uruchomić make init.
$etykieta = 'Katalog produktów';
$idKategoriiGlownej = (int) Configuration::get('PS_HOME_CATEGORY');
$etykiety = [];
$adresy = [];
foreach (Language::getIDs(false) as $idJezyka) {
    $etykiety[$idJezyka] = $etykieta;
    $adresy[$idJezyka] = $context->link->getCategoryLink($idKategoriiGlownej, null, $idJezyka, null, $idShop);
}

$znajdzLink = fn () => (int) $db->getValue(
    'SELECT id_linksmenutop FROM ' . _DB_PREFIX_ . 'linksmenutop_lang
     WHERE label = "' . pSQL($etykieta) . '" AND id_shop = ' . $idShop
);
$idLinku = $znajdzLink();
if ($idLinku) {
    // Adres zależy od domeny z .env, więc odświeżamy go przy każdym make init.
    Ps_MenuTopLinks::update($adresy, $etykiety, 0, $idShop, $idLinku);
} else {
    if (!Ps_MenuTopLinks::add($adresy, $etykiety, 0, $idShop)) {
        throw new RuntimeException('Nie udalo sie dodac linku menu');
    }
    $idLinku = $znajdzLink();
}
ustaw('MOD_BLOCKTOPMENU_ITEMS', 'LNK' . $idLinku);

// L1: w lewej kolumnie drzewo od bieżącej kategorii (w źródle na liście „Sopranowe” jest tylko „Sopranowe”),
// bez pustych bloków „Marki” i „Dostawcy”.
ustaw('BLOCK_CATEG_ROOT_CATEGORY', 1); // Ps_CategoryTree::CATEGORY_ROOT_CURRENT
foreach (['ps_brandlist', 'ps_supplierlist'] as $nazwa) {
    $modul = Module::getInstanceByName($nazwa);
    if ($modul && $modul->isRegisteredInHook('displayLeftColumn') && !$modul->unregisterHook('displayLeftColumn')) {
        throw new RuntimeException("Nie udalo sie odpiac $nazwa od lewej kolumny");
    }
}

// L3: 16 produktów na stronę.
ustaw('PS_PRODUCTS_PER_PAGE', 16);

// L4: bez serduszka ulubionych. W źródle nie ma list życzeń, a serduszko na karcie produktu
// wychodziło na telefonie poza ekran (P3). Znaczek „Nowy” jest ukryty w CSS, bo PS_NB_DAYS_NEW_PRODUCT = 0
// wyczyściłby stronę „Nowe produkty” (wszystkie produkty przyszły jednym importem).
$wishlist = Module::getInstanceByName('blockwishlist');
if ($wishlist && Module::isEnabled('blockwishlist') && !$wishlist->disable()) {
    throw new RuntimeException('Nie udalo sie wylaczyc blockwishlist');
}

// Obrazy sklepu leżą w motywie (shop/themes/gitara/assets), który init.sh kopiuje do sklepu.
// PrestaShop szuka logo w img/, a obrazu ps_banner w katalogu modułu, więc kopiujemy je tam,
// tylko gdy plik się zmienił.
function skopiuj(string $skad, string $dokad): void
{
    if (!is_file($skad)) {
        throw new RuntimeException("Brak pliku $skad");
    }
    if (is_file($dokad) && md5_file($skad) === md5_file($dokad)) {
        return;
    }
    if (!copy($skad, $dokad)) {
        throw new RuntimeException("Nie udalo sie skopiowac $skad do $dokad");
    }
    chown($dokad, 'www-data');
    chgrp($dokad, 'www-data');
}

$obrazy = _PS_ALL_THEMES_DIR_ . 'gitara/assets/';

// Logo sklepu zamiast „my store” (roznice.md, sekcja 8). Maile i faktury biorą PS_LOGO, gdy nie mają własnego.
$plikLogo = 'gitara-logo.png';
skopiuj($obrazy . 'logo.png', _PS_IMG_DIR_ . $plikLogo);
[$szerokoscLogo, $wysokoscLogo] = getimagesize(_PS_IMG_DIR_ . $plikLogo);
ustaw('PS_LOGO', $plikLogo);
ustaw('SHOP_LOGO_WIDTH', $szerokoscLogo);
ustaw('SHOP_LOGO_HEIGHT', $wysokoscLogo);

// G1: strona główna. W źródle pod sliderem są tylko „Popularne produkty” (ps_featuredproducts), obraz
// sklepu z godzinami otwarcia (ps_banner) i tekst (ps_customtext, treść w cms/strona-glowna.html).
// „Nowe produkty”, „Promocje” i „Najczęściej kupowane” są dodatkowe, więc odpinamy je od displayHome.
foreach (['ps_specials', 'ps_newproducts', 'ps_bestsellers'] as $nazwa) {
    $modul = Module::getInstanceByName($nazwa);
    if ($modul && $modul->isRegisteredInHook('displayHome') && !$modul->unregisterHook('displayHome')) {
        throw new RuntimeException("Nie udalo sie odpiac $nazwa od strony glownej");
    }
}

// Obraz ps_banner zamiast demo „20% OFF ON CLOTHES”. Bez linku moduł prowadzi na stronę główną.
$plikBanera = 'gitara-baner.jpg';
$baner = Module::getInstanceByName('ps_banner');
if (!$baner) {
    throw new RuntimeException('Brak modulu ps_banner');
}
skopiuj($obrazy . 'baner.jpg', _PS_MODULE_DIR_ . 'ps_banner/img/' . $plikBanera);
foreach (Language::getIDs(false) as $idJezyka) {
    if (Configuration::get('BANNER_IMG', $idJezyka) !== $plikBanera) {
        Configuration::updateValue('BANNER_IMG', [$idJezyka => $plikBanera]);
    }
    $opis = 'Sklep muzyczny – godziny otwarcia';
    if (Configuration::get('BANNER_DESC', $idJezyka) !== $opis) {
        Configuration::updateValue('BANNER_DESC', [$idJezyka => $opis]);
    }
}
if (!$baner->isRegisteredInHook('displayHome') && !$baner->registerHook('displayHome')) {
    throw new RuntimeException('Nie udalo sie podpiac ps_banner do strony glownej');
}

// Pod tekstem źródło ma drugi raz menu górne („Katalog produktów”), tylko na komputerze (szablon menu
// ma hidden-sm-down). To ten sam moduł podpięty do displayHome, więc robimy tak samo. Obie kopie mają
// id _desktop_top_menu, ale JS Classic tylko przenosi ich zawartość do hamburgera i z powrotem,
// a jest ona taka sama, więc menu na telefonie działa jak dotąd (tak samo jest w źródle).
if (!$menu->isRegisteredInHook('displayHome') && !$menu->registerHook('displayHome')) {
    throw new RuntimeException('Nie udalo sie podpiac ps_mainmenu do strony glownej');
}

// Kolejność jak w źródle: slider, produkty, obraz sklepu, tekst, menu. Pozostałe moduły (np. dodane
// później w panelu) zostają za nimi w dotychczasowej kolejności.
$idHookaGlownej = (int) Hook::getIdByName('displayHome');
$wHooku = $db->executeS(
    'SELECT m.name, hm.id_module, hm.position FROM ' . _DB_PREFIX_ . 'hook_module hm
     JOIN ' . _DB_PREFIX_ . 'module m ON m.id_module = hm.id_module
     WHERE hm.id_hook = ' . $idHookaGlownej . ' AND hm.id_shop = ' . $idShop . '
     ORDER BY hm.position'
);
$kolejnosc = ['ps_imageslider', 'ps_featuredproducts', 'ps_banner', 'ps_customtext', 'ps_mainmenu'];
usort($wHooku, function (array $a, array $b) use ($kolejnosc): int {
    $pa = array_search($a['name'], $kolejnosc, true);
    $pb = array_search($b['name'], $kolejnosc, true);
    return [$pa === false ? PHP_INT_MAX : $pa, (int) $a['position']]
        <=> [$pb === false ? PHP_INT_MAX : $pb, (int) $b['position']];
});
foreach ($wHooku as $i => $wiersz) {
    if ((int) $wiersz['position'] !== $i + 1) {
        $db->update('hook_module', ['position' => $i + 1],
            'id_hook = ' . $idHookaGlownej . ' AND id_shop = ' . $idShop . ' AND id_module = ' . (int) $wiersz['id_module']);
    }
}

// „Popularne produkty” pokazują produkty przypisane wprost do kategorii HOME_FEATURED_CAT (tu: strona
// główna), a import przypisuje produkty tylko do ich kategorii i jej przodków bez strony głównej.
// Bez tego sekcja jest pusta i się nie wyświetla. Przypinamy po 2 dostępne produkty ze zdjęciem
// z pierwszych kategorii menu. Tylko gdy na stronie głównej nie ma jeszcze żadnego produktu, więc
// ręczny wybór w panelu (Katalog > Produkty > Powiązania) nie zostanie nadpisany. Import przy
// aktualizacji produktów nie zmienia ich kategorii, więc przypisanie zostaje po ponownym imporcie.
ustaw('HOME_FEATURED_CAT', $idKategoriiGlownej);
ustaw('HOME_FEATURED_NBR', 8);
$naGlownej = (int) $db->getValue(
    'SELECT COUNT(*) FROM ' . _DB_PREFIX_ . 'category_product WHERE id_category = ' . $idKategoriiGlownej
);
if ($naGlownej === 0) {
    $kategorie = $db->executeS(
        'SELECT c.id_category FROM ' . _DB_PREFIX_ . 'category c
         JOIN ' . _DB_PREFIX_ . 'category_shop cs ON cs.id_category = c.id_category AND cs.id_shop = ' . $idShop . '
         WHERE c.id_parent = ' . $idKategoriiGlownej . ' AND c.active = 1
         ORDER BY cs.position'
    );
    $wybrane = [];
    foreach ($kategorie as $kategoria) {
        $produkty = $db->executeS(
            'SELECT DISTINCT p.id_product FROM ' . _DB_PREFIX_ . 'category_product cp
             JOIN ' . _DB_PREFIX_ . 'product_shop p ON p.id_product = cp.id_product AND p.id_shop = ' . $idShop . '
             JOIN ' . _DB_PREFIX_ . 'stock_available sa ON sa.id_product = p.id_product AND sa.id_product_attribute = 0
             JOIN ' . _DB_PREFIX_ . 'image i ON i.id_product = p.id_product AND i.cover = 1
             WHERE cp.id_category = ' . (int) $kategoria['id_category'] . '
               AND p.active = 1 AND p.visibility IN ("both", "catalog") AND sa.quantity > 0
             ORDER BY p.id_product
             LIMIT 2'
        );
        foreach ($produkty as $produkt) {
            $wybrane[] = (int) $produkt['id_product'];
        }
        if (count($wybrane) >= 8) {
            break;
        }
    }
    foreach (array_slice($wybrane, 0, 8) as $idProduktu) {
        if (!(new Product($idProduktu))->addToCategories([$idKategoriiGlownej])) {
            throw new RuntimeException("Nie udalo sie dodac produktu $idProduktu do strony glownej");
        }
    }
    if (!$wybrane) {
        echo "UWAGA: brak produktów do sekcji „Popularne produkty” (czy import był uruchomiony?)\n";
    }
}

echo "Układ (menu, strona główna, lewa kolumna, lista produktów): OK\n";
