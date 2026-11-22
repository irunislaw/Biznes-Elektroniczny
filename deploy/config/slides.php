<?php

// Treść i linki slajdów zmieniaj tutaj. Kolejność wpisów to kolejność w karuzeli.
// Klucze dunlop/hohner/tc_electronic identyfikują slajdy: nie zmieniaj ich przy zmianie zdjęcia lub tekstu.
// Puste title i text oznaczają sam obraz, jak w źródle.
$slides = [
    'dunlop' => [
        'image' => 'slide_dunlop.webp',
        'title' => '',
        'text' => '',
        'alt' => 'Produkty marki Dunlop',
        'category_id' => 16, //tymczasowo link do akcesoriów do ukulele
    ],
    'hohner' => [
        'image' => 'slide_hohner.webp',
        'title' => '',
        'text' => '',
        'alt' => 'Harmonijki i instrumenty marki Hohner',
        'category_id' => 55, // Harmonijki ustne.
    ],
    'tc_electronic' => [
        'image' => 'slide_tc_electronic.webp',
        'title' => '',
        'text' => '',
        'alt' => 'Produkty marki tc electronic',
        'category_id' => 29, //tymczasowo link do syntezatorów modułowych
    ],
];

require_once '/var/www/html/config/config.inc.php';
require_once __DIR__ . '/helpers.php';

$imageslider = Module::getInstanceByName('ps_imageslider');
if (!$imageslider || !Module::isEnabled('ps_imageslider')) {
    throw new RuntimeException('Brak aktywnego modulu ps_imageslider');
}

$context = Context::getContext();
$idShop = (int) $context->shop->id;
$idJezykow = Language::getIDs(false);
$obrazy = _PS_ALL_THEMES_DIR_ . 'gitara/assets/slides/';
$katalogModulu = _PS_MODULE_DIR_ . 'ps_imageslider/images/';

if (!$slides) {
    throw new RuntimeException('Lista slajdow jest pusta');
}
foreach ($slides as $key => $dane) {
    if (!is_file($obrazy . $dane['image'])) {
        throw new RuntimeException('Brak obrazu slajdu: ' . $dane['image']);
    }
    $kategoria = new Category((int) $dane['category_id']);
    if (!Validate::isLoadedObject($kategoria) || !$kategoria->active || !$kategoria->isAssociatedToShop($idShop)) {
        throw new RuntimeException("Nie znaleziono aktywnej kategorii slajdu $key w tym sklepie");
    }
}

if (!$imageslider->isRegisteredInHook('displayHome') && !$imageslider->registerHook('displayHome')) {
    throw new RuntimeException('Nie udalo sie podpiac slidera do strony glownej');
}

$aktywneId = [];
$pozycja = 0;
foreach ($slides as $key => $dane) {
    // ID przechowujemy w konfiguracji. Dzięki temu zmiana zdjęcia, tekstu i kolejności nie tworzy kopii.
    $kluczKonfiguracji = 'GITARA_SLIDE_' . strtoupper($key);
    $idSlajdu = (int) Configuration::get($kluczKonfiguracji);
    $slide = new Ps_HomeSlide($idSlajdu);
    $istnieje = Validate::isLoadedObject($slide);
    if ($istnieje && !in_array($idShop, Ps_HomeSlide::getAssociatedIdsShop($idSlajdu), true)) {
        throw new RuntimeException("Slajd $key nalezy do innego sklepu");
    }

    skopiuj($obrazy . $dane['image'], $katalogModulu . $dane['image']);
    $zmiana = !$istnieje || (int) $slide->active !== 1 || (int) $slide->position !== $pozycja;
    $slide->active = 1;
    $slide->position = $pozycja++;

    // PrestaShop przechowuje te pola osobno dla każdego języka.
    foreach ($idJezykow as $idJezyka) {
        $pola = [
            'image' => $dane['image'],
            'title' => $dane['title'],
            'description' => $dane['text'],
            'legend' => $dane['alt'],
            'url' => $context->link->getCategoryLink((int) $dane['category_id'], null, $idJezyka, null, $idShop),
        ];
        foreach ($pola as $pole => $wartosc) {
            if (($slide->{$pole}[$idJezyka] ?? '') !== $wartosc) {
                $slide->{$pole}[$idJezyka] = $wartosc;
                $zmiana = true;
            }
        }
    }

    if ($zmiana && !($istnieje ? $slide->update() : $slide->add())) {
        throw new RuntimeException("Nie udalo sie zapisac slajdu $key");
    }
    ustaw($kluczKonfiguracji, (int) $slide->id);
    $aktywneId[] = (int) $slide->id;
}

foreach ($imageslider->getSlides(null, true) as $wiersz) {
    if (!in_array((int) $wiersz['id_slide'], $aktywneId, true) && (int) $wiersz['active'] === 1) {
        $slide = new Ps_HomeSlide((int) $wiersz['id_slide']);
        $slide->active = 0;
        if (!$slide->update()) {
            throw new RuntimeException('Nie udalo sie wylaczyc starego slajdu');
        }
    }
}

$imageslider->clearCache();
echo 'Slajdy: OK (' . count($aktywneId) . ")\n";
