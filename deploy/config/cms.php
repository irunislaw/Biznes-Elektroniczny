<?php
// Strony CMS, stopka i tekst na stronie głównej. Treści są w deploy/config/cms/.
// Strony szukamy po adresie, nie po id, więc działa to też po zrzucie bazy i przy DANE=0.

require_once '/var/www/html/config/config.inc.php';

const SHOP_NAME = 'Gitara Siema';
const CONTENT_DIR = '/opt/prestashop-config/cms';
const CMS_CATEGORY_ID = 1;
const FOOTER_HOOK = 'displayFooter';

// W tej kolejności strony będą w stopce. 'demo' to strona z instalatora do przerobienia.
$pages = [
    [
        'link_rewrite' => 'o-sklepie',
        'demo' => 'about-us',
        'meta_title' => 'O sklepie',
        'meta_description' => SHOP_NAME . ' – sklep muzyczny z ukulele, syntezatorami, perkusją, harmonijkami ustnymi i przewodami audio.',
    ],
    [
        'link_rewrite' => 'regulamin',
        'demo' => 'terms-and-conditions-of-use',
        'meta_title' => 'Regulamin',
        'meta_description' => 'Regulamin sklepu ' . SHOP_NAME . ': zamówienia, ceny, płatności, dostawa, odstąpienie od umowy i reklamacje.',
    ],
    [
        'link_rewrite' => 'polityka-prywatnosci',
        'demo' => null,
        'meta_title' => 'Polityka prywatności',
        'meta_description' => 'Jakie dane zbiera sklep ' . SHOP_NAME . ', w jakim celu, jakie prawa ma klient i jakich plików cookies używamy.',
    ],
    [
        'link_rewrite' => 'dostawa',
        'demo' => 'delivery',
        'meta_title' => 'Dostawa',
        'meta_description' => 'Kurier za 14,99 zł i kurier ekspres za 24,99 zł. Darmowa dostawa powyżej 2000 zł brutto, tylko w Polsce.',
    ],
    [
        'link_rewrite' => 'formy-platnosci',
        'demo' => 'secure-payment',
        'meta_title' => 'Formy płatności',
        'meta_description' => 'Przelew tradycyjny lub płatność przy odbiorze. Faktura VAT do każdego zamówienia.',
    ],
];

// Tylko wyłączamy, nie usuwamy
$disabledPages = ['legal-notice'];

function findCmsId(string $linkRewrite, int $langId, int $shopId): int
{
    return (int) Db::getInstance()->getValue(
        'SELECT id_cms FROM `' . _DB_PREFIX_ . 'cms_lang`'
        . " WHERE link_rewrite = '" . pSQL($linkRewrite) . "'"
        . ' AND id_lang = ' . $langId . ' AND id_shop = ' . $shopId
        . ' ORDER BY id_cms'
    );
}

function readContent(string $name): string
{
    $path = CONTENT_DIR . '/' . $name . '.html';
    $content = is_file($path) ? file_get_contents($path) : false;

    if ($content === false) {
        throw new RuntimeException("Brak pliku z trescia: $path");
    }

    if (str_starts_with($content, "\xEF\xBB\xBF") || !mb_check_encoding($content, 'UTF-8')) {
        throw new RuntimeException("Plik $path musi byc zapisany w UTF-8 bez BOM");
    }

    return trim(str_replace("\r\n", "\n", $content));
}

// Zapisuje tylko wtedy, gdy wartość się zmieniła
function updateText(string $table, string $column, string $value, string $where): void
{
    $db = Db::getInstance();
    $current = $db->getValue('SELECT `' . bqSQL($column) . '` FROM `' . _DB_PREFIX_ . $table . '` WHERE ' . $where);

    if ($current === false) {
        throw new RuntimeException("Brak wiersza w $table ($where)");
    }

    if ((string) $current === $value) {
        return;
    }

    // true, bo inaczej pSQL wytnie HTML
    if (!$db->update($table, [$column => pSQL($value, true)], $where)) {
        throw new RuntimeException("Nie udalo sie zapisac $table.$column ($where)");
    }
}

$db = Db::getInstance();
$langId = (int) Language::getIdByIso('pl');
$shopId = (int) Configuration::get('PS_SHOP_DEFAULT');
$countryId = (int) Country::getByIso('PL');

if ($langId <= 0 || $shopId <= 0 || $countryId <= 0) {
    throw new RuntimeException('Nie znaleziono jezyka pl, domyslnego sklepu albo kraju PL');
}

$cmsIds = [];

foreach ($pages as $page) {
    $name = $page['link_rewrite'];
    $cmsId = findCmsId($name, $langId, $shopId);

    if (!$cmsId && $page['demo'] !== null) {
        $cmsId = findCmsId($page['demo'], $langId, $shopId);
    }

    $cms = new CMS($cmsId ?: null);

    $values = [
        'meta_title' => $page['meta_title'],
        'meta_description' => $page['meta_description'],
        'meta_keywords' => '', // demo ma tu angielskie słowa kluczowe
        'link_rewrite' => $name,
        'content' => readContent($name),
    ];

    $changed = (int) $cms->active !== 1;
    $cms->active = 1;

    foreach ($values as $field => $value) {
        // PrestaShop czyści HTML przy zapisie, więc porównujemy z wyczyszczoną wersją
        $expected = $field === 'content' ? Tools::purifyHTML($value) : $value;

        if ((string) ($cms->{$field}[$langId] ?? '') !== $expected) {
            $cms->{$field}[$langId] = $value;
            $changed = true;
        }
    }

    if (!Validate::isLoadedObject($cms)) {
        $cms->id_cms_category = CMS_CATEGORY_ID;

        if (!$cms->add()) {
            throw new RuntimeException("Nie udalo sie dodac strony $name");
        }
    } elseif ($changed && !$cms->update()) {
        throw new RuntimeException("Nie udalo sie zapisac strony $name");
    }

    $cmsIds[$name] = (int) $cms->id;
}

foreach ($disabledPages as $name) {
    $cmsId = findCmsId($name, $langId, $shopId);

    if (!$cmsId) {
        continue;
    }

    $cms = new CMS($cmsId);

    if ($cms->active) {
        $cms->active = 0;

        if (!$cms->update()) {
            throw new RuntimeException("Nie udalo sie wylaczyc strony $name");
        }
    }
}

// Regulamin w zamówieniu oraz nazwa i adres sklepu
$settings = [
    'PS_CONDITIONS_CMS_ID' => (string) $cmsIds['regulamin'],
    'PS_SHOP_NAME' => SHOP_NAME,
    'PS_SHOP_ADDR1' => 'ul. Test 1',
    'PS_SHOP_CODE' => '00-001',
    'PS_SHOP_CITY' => 'Warszawa',
    'PS_SHOP_COUNTRY_ID' => (string) $countryId,
    'PS_SHOP_PHONE' => '+48 000 000 000',
];

foreach ($settings as $key => $value) {
    if ((string) Configuration::get($key) === $value) {
        continue;
    }

    if (!Configuration::updateValue($key, $value)) {
        throw new RuntimeException("Nie udalo sie ustawic $key");
    }
}

// Stopka: dwa bloki linków, w kolejności jak na stronie
$hookId = (int) Hook::getIdByName(FOOTER_HOOK);
$blocks = $db->executeS(
    'SELECT lb.id_link_block FROM `' . _DB_PREFIX_ . 'link_block` lb'
    . ' INNER JOIN `' . _DB_PREFIX_ . 'link_block_shop` lbs ON lbs.id_link_block = lb.id_link_block'
    . ' WHERE lb.id_hook = ' . $hookId . ' AND lbs.id_shop = ' . $shopId
    . ' ORDER BY lbs.position, lb.id_link_block'
);
$blockCount = is_array($blocks) ? count($blocks) : 0;

if ($hookId <= 0 || $blockCount !== 2) {
    throw new RuntimeException("W stopce (ps_linklist, displayFooter) powinny byc 2 bloki linkow, jest $blockCount");
}

[$productsBlockId, $infoBlockId] = array_map('intval', array_column($blocks, 'id_link_block'));

// Format jak w module (id jako napisy)
$infoContent = json_encode([
    'cms' => array_map('strval', array_values($cmsIds)),
    'product' => [false],
    'static' => ['contact', 'sitemap'],
]);

updateText('link_block_lang', 'name', 'Produkty', "id_link_block = $productsBlockId AND id_lang = $langId");
updateText('link_block_lang', 'name', 'Nasza firma', "id_link_block = $infoBlockId AND id_lang = $langId");
updateText('link_block', 'content', $infoContent, "id_link_block = $infoBlockId");

// Tekst na stronie głównej (ps_customtext)
$infoId = (int) $db->getValue(
    'SELECT id_info FROM `' . _DB_PREFIX_ . 'info_shop` WHERE id_shop = ' . $shopId . ' ORDER BY id_info'
);

if ($infoId <= 0) {
    throw new RuntimeException('Nie znaleziono bloku tekstowego ps_customtext');
}

updateText(
    'info_lang',
    'text',
    readContent('strona-glowna'),
    "id_info = $infoId AND id_shop = $shopId AND id_lang = $langId"
);

echo "Strony CMS i stopka: OK\n";
