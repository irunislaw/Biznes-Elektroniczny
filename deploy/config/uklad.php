<?php

// Układ nagłówka, strony głównej i listy produktów jak w sklepie źródłowym (BE-33, docs/wyglad/roznice.md).
// Tylko ustawienia modułów i konfiguracji. Zmiany wyglądu są w shop/themes/gitara/assets/css/custom.css.
// Przy drugim uruchomieniu niczego nie zmienia.

require_once '/var/www/html/config/config.inc.php';
require_once __DIR__ . '/helpers.php';

// Moduł menu dołącza klasę Ps_MenuTopLinks zwykłym require, więc nie wczytujemy jej osobno
// (drugie wczytanie kończy się błędem „Cannot declare class”).
$menu = Module::getInstanceByName('ps_mainmenu');
if (!$menu) {
    throw new RuntimeException('Brak modulu ps_mainmenu');
}

$context = Context::getContext();
$idShop = (int) $context->shop->id;
$db = Db::getInstance();

$obrazy = _PS_ALL_THEMES_DIR_ . 'gitara/assets/';
$idKategoriiGlownej = (int) Configuration::get('PS_HOME_CATEGORY');

// K0: kategoria główna („Katalog produktów” w menu) jak w źródle: nazwa „Katalog produktów Gitara No.1”,
// adres /2-katalog-produktow-gitara-no1, opis pod nazwą i obrazek. Nazwa jest w nagłówku tej strony i w tytule
// drzewa kategorii w lewej kolumnie. Okruszki jej nie pokazują (kategoria główna jest pomijana), a import
// (deploy/import/import.py) jej nie zmienia. Musi być przed N1, bo adres w menu zależy od link_rewrite.
$kategoriaGlowna = new Category($idKategoriiGlownej);
$zmiana = false;
$polaKategoriiGlownej = [
    'name' => 'Katalog produktów Gitara No.1',
    'link_rewrite' => 'katalog-produktow-gitara-no1',
    'description' => '<p>Sklep muzyczny Gitara No.1 - oferta sklepu internetowego www.gitara-sklep.pl</p>',
];
foreach (Language::getIDs(false) as $idJezyka) {
    foreach ($polaKategoriiGlownej as $pole => $wartosc) {
        if (($kategoriaGlowna->{$pole}[$idJezyka] ?? '') !== $wartosc) {
            $kategoriaGlowna->{$pole}[$idJezyka] = $wartosc;
            $zmiana = true;
        }
    }
}
if ($zmiana && !$kategoriaGlowna->update()) {
    throw new RuntimeException('Nie udalo sie zmienic nazwy kategorii glownej');
}

// Obrazek kategorii: oryginał img/c/<id>.jpg i miniatury dla typów z zakresu kategorii (jak przy
// wgraniu w panelu). Plik ma już wymiary category_default (141 × 180), który pokazuje nagłówek kategorii.
$plikKategorii = _PS_CAT_IMG_DIR_ . $idKategoriiGlownej . '.jpg';
$nowyObrazek = skopiuj($obrazy . 'katalog-produktow.jpg', $plikKategorii);
foreach (ImageType::getImagesTypes('categories') as $typ) {
    $miniatura = _PS_CAT_IMG_DIR_ . $idKategoriiGlownej . '-' . $typ['name'] . '.jpg';
    if (!$nowyObrazek && is_file($miniatura)) {
        continue;
    }
    if (!ImageManager::resize($plikKategorii, $miniatura, (int) $typ['width'], (int) $typ['height'], 'jpg')) {
        throw new RuntimeException("Nie udalo sie zrobic miniatury $miniatura");
    }
    chown($miniatura, 'www-data');
    chgrp($miniatura, 'www-data');
}

// N1: w menu górnym jedna pozycja „Katalog produktów” prowadząca do kategorii głównej, jak w źródle.
// Wyszukiwarka mieści się wtedy w tym samym wierszu bez zmian w CSS. Uwaga: import (deploy/import/import.py,
// setup_ps_main_menu) wpisuje do menu kategorie główne, więc po ponownym imporcie trzeba uruchomić make init.
$etykieta = 'Katalog produktów';
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

// P1: wyłącznie modułu blockreassurance z tekstem demo
if (Module::isEnabled('blockreassurance')) {
    $reassurance = Module::getInstanceByName('blockreassurance');

    if (!$reassurance || !$reassurance->disable()) {
        throw new RuntimeException(
            'Nie udalo sie wylaczyc blockreassurance'
        );
    }
}

// P4: pod opisem produktu źródło ma tylko blok „Zobacz także” z 3 produktami. U nas była sekcja
// „Komentarze (0)” (productcomments) i 16 produktów z tej samej kategorii (ps_categoryproducts), przez co
// karta produktu na telefonie była ponad dwa razy dłuższa niż w źródle. Komentarzy w źródle nie ma wcale,
// więc moduł jest wyłączony. Produkty z kategorii zostają, ale 3 i z tytułem jak w źródle (tłumaczenie niżej).
$komentarze = Module::getInstanceByName('productcomments');
if ($komentarze && Module::isEnabled('productcomments') && !$komentarze->disable()) {
    throw new RuntimeException('Nie udalo sie wylaczyc productcomments');
}
ustaw('CATEGORYPRODUCTS_DISPLAY_PRODUCTS', 3);

// Bez znaczka „Obecnie brak na stanie” na kafelkach, jak w źródle. Produkty bez stanu nadal mają
// informację o dostępności na karcie produktu i nie da się ich dodać do koszyka.
ustaw('PS_SHOW_LABEL_OOS_LISTING_PAGES', 0);

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
$plikBanera = 'gitara-baner.webp';
$baner = Module::getInstanceByName('ps_banner');
if (!$baner) {
    throw new RuntimeException('Brak modulu ps_banner');
}
skopiuj($obrazy . 'baner.webp', _PS_MODULE_DIR_ . 'ps_banner/img/' . $plikBanera);
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

// Ustawia moduły z listy na początku hooka, w podanej kolejności. Pozostałe moduły (np. dodane
// później w panelu) zostają za nimi w dotychczasowej kolejności.
function ustawKolejnosc(string $hook, array $kolejnosc): void
{
    $db = Db::getInstance();
    $idShop = (int) Context::getContext()->shop->id;
    $idHooka = (int) Hook::getIdByName($hook);
    $wHooku = $db->executeS(
        'SELECT m.name, hm.id_module, hm.position FROM ' . _DB_PREFIX_ . 'hook_module hm
         JOIN ' . _DB_PREFIX_ . 'module m ON m.id_module = hm.id_module
         WHERE hm.id_hook = ' . $idHooka . ' AND hm.id_shop = ' . $idShop . '
         ORDER BY hm.position'
    );
    usort($wHooku, function (array $a, array $b) use ($kolejnosc): int {
        $pa = array_search($a['name'], $kolejnosc, true);
        $pb = array_search($b['name'], $kolejnosc, true);
        return [$pa === false ? PHP_INT_MAX : $pa, (int) $a['position']]
            <=> [$pb === false ? PHP_INT_MAX : $pb, (int) $b['position']];
    });
    foreach ($wHooku as $i => $wiersz) {
        if ((int) $wiersz['position'] !== $i + 1) {
            $db->update('hook_module', ['position' => $i + 1],
                'id_hook = ' . $idHooka . ' AND id_shop = ' . $idShop . ' AND id_module = ' . (int) $wiersz['id_module']);
        }
    }
}

// Kolejność jak w źródle: slider, produkty, obraz sklepu, tekst, menu.
ustawKolejnosc('displayHome', ['ps_imageslider', 'ps_featuredproducts', 'ps_banner', 'ps_customtext', 'ps_mainmenu']);

// Zgody w formularzu danych klienta (krok „Dane osobowe” w zamówieniu i rejestracja) jak w źródle:
// oferty partnerów (pole PrestaShop, zawsze pierwsze), newsletter (ps_emailsubscription), regulamin
// i polityka prywatności (psgdpr). Zgody „Wiadomość o przetwarzaniu danych osobowych” (ps_dataprivacy,
// z angielskim tekstem modułu) w źródle nie ma, a akceptację polityki prywatności daje już psgdpr.
ustawKolejnosc('additionalCustomerFormFields', ['ps_emailsubscription', 'psgdpr']);
$prywatnosc = Module::getInstanceByName('ps_dataprivacy');
if ($prywatnosc && Module::isEnabled('ps_dataprivacy') && !$prywatnosc->disable()) {
    throw new RuntimeException('Nie udalo sie wylaczyc ps_dataprivacy');
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

// Tłumaczenia nadpisane tak, żeby napisy były jak w źródle.
// S1: link do korekt płatności w stopce i na stronie „Moje konto” nazwany jak w źródle. PrestaShop 8
// tłumaczy „Credit slips” jako „Potwierdzenia zwrotów”, a źródło (1.7) jako „Moje pokwitowania - korekty
// płatności”. Nadpisanie jak z panelu (Międzynarodowe > Tłumaczenia): wiersz w ps_translation bez motywu,
// w obu domenach, w których jest ten napis (moduł: stopka gościa, motyw: stopka klienta i „Moje konto”).
// Katalog tłumaczeń jest w cache, więc zmiana jest widoczna po wyczyszczeniu cache (robi to make init).
// P4: tytuł bloku ps_categoryproducts „Zobacz także” zamiast „16 innych produktów w tej samej kategorii:”.
// Szablon podstawia liczbę za %s, a tłumaczenie bez %s ją po prostu pomija.
// K3: przycisk w koszyku i w okienku po dodaniu do koszyka „Realizuj zamówienie” jak w źródle (PrestaShop 8:
// „Przejdź do realizacji zamówienia”). Testy e2e szukają przycisku po tym tekście (tests/pages/checkout.ts).
$idPolskiego = (int) Language::getIdByIso('pl');
$tlumaczenia = [
    ['Credit slips', 'ModulesCustomeraccountlinksAdmin', 'Moje pokwitowania - korekty płatności'],
    ['Credit slips', 'ShopThemeCustomeraccount', 'Moje pokwitowania - korekty płatności'],
    ['%s other product in the same category:', 'ShopThemeCatalog', 'Zobacz także'],
    ['%s other products in the same category:', 'ShopThemeCatalog', 'Zobacz także'],
    ['Proceed to checkout', 'ShopThemeActions', 'Realizuj zamówienie'],
];
foreach ($tlumaczenia as [$klucz, $domena, $tekst]) {
    $warunek = 'id_lang = ' . $idPolskiego . ' AND `key` = "' . pSQL($klucz) . '" AND domain = "' . pSQL($domena) . '" AND theme IS NULL';
    $wiersz = $db->getRow('SELECT id_translation, translation FROM ' . _DB_PREFIX_ . 'translation WHERE ' . $warunek);
    if ($wiersz && $wiersz['translation'] === $tekst) {
        continue;
    }
    $zapisano = $wiersz
        ? $db->update('translation', ['translation' => pSQL($tekst)], 'id_translation = ' . (int) $wiersz['id_translation'])
        : $db->insert('translation', ['id_lang' => $idPolskiego, 'key' => pSQL($klucz), 'translation' => pSQL($tekst), 'domain' => pSQL($domena)]);
    if (!$zapisano) {
        throw new RuntimeException("Nie udalo sie zapisac tlumaczenia $klucz ($domena)");
    }
}

echo "Układ (menu, strona główna, lewa kolumna, lista produktów): OK\n";
