<?php
// Uzupełnia pliki zdjęć produktów w img/p dla zdjęć zapisanych w bazie (ps_image):
// - oryginał <id>.jpg, jeśli go nie ma, a podano katalog z wynikami scrapera (zapasowa ścieżka make init),
// - brakujące miniatury wszystkich typów zdjęć produktów (np. large_default pominięte w archiwum).
// Tak samo jak przy wysyłaniu zdjęć przez Webservice (WebserviceSpecificManagementImages).
//
// Uruchamia go zdjecia.sh w kilku procesach naraz, każdy dla innej części zdjęć:
//   php zdjecia.php <nr części> <liczba części> [katalog scraper-results]

require_once '/var/www/html/config/config.inc.php';

const POKAZ_BRAKI = 5;

$czesc = (int) ($argv[1] ?? 0);
$czesci = max(1, (int) ($argv[2] ?? 1));
$zrodlo = rtrim($argv[3] ?? '', '/');

// Import wysyła zdjęcia produktu w kolejności image_files, więc zdjęcie na pozycji N
// to N-ty plik z image_files produktu o reference = id ze sklepu źródłowego.
$pliki = [];

if ($zrodlo !== '') {
    $produkty = json_decode(file_get_contents("$zrodlo/results.json"), true, 512, JSON_THROW_ON_ERROR);

    foreach ($produkty as $produkt) {
        foreach (array_values($produkt['image_files']) as $i => $plik) {
            $pliki[(string) $produkt['id']][$i + 1] = "$zrodlo/$plik";
        }
    }
}

$typy = ImageType::getImagesTypes('products');
$zdjecia = Db::getInstance()->executeS(
    'SELECT i.id_image, i.position, p.reference FROM `' . _DB_PREFIX_ . 'image` i'
    . ' JOIN `' . _DB_PREFIX_ . 'product` p ON p.id_product = i.id_product'
    . ' WHERE MOD(i.id_image, ' . $czesci . ') = ' . $czesc
);

$oryginaly = 0;
$miniatury = 0;
$braki = 0;

foreach ($zdjecia as $zdjecie) {
    $id = (int) $zdjecie['id_image'];
    $sciezka = _PS_PRODUCT_IMG_DIR_ . Image::getImgFolderStatic($id) . $id;

    if (!is_file("$sciezka.jpg")) {
        $plik = $pliki[$zdjecie['reference']][(int) $zdjecie['position']] ?? null;

        if ($plik === null || !is_file($plik)) {
            if (++$braki <= POKAZ_BRAKI) {
                fwrite(STDERR, "Brak pliku zdjęcia $id (produkt {$zdjecie['reference']}, pozycja {$zdjecie['position']})\n");
            }
            continue;
        }

        (new Image($id))->createImgFolder();

        if (!ImageManager::resize($plik, "$sciezka.jpg")) {
            throw new RuntimeException("Nie udalo sie zapisac zdjecia $id z $plik");
        }
        ++$oryginaly;
    }

    foreach ($typy as $typ) {
        $miniatura = "$sciezka-" . stripslashes($typ['name']) . '.jpg';

        if (is_file($miniatura)) {
            continue;
        }

        if (!ImageManager::resize("$sciezka.jpg", $miniatura, (int) $typ['width'], (int) $typ['height'], 'jpg')) {
            throw new RuntimeException("Nie udalo sie utworzyc miniatury $miniatura");
        }
        ++$miniatury;
    }
}

printf(
    "Część %d/%d: zdjęć %d, nowe oryginały %d, nowe miniatury %d, brak pliku %d\n",
    $czesc + 1,
    $czesci,
    count($zdjecia),
    $oryginaly,
    $miniatury,
    $braki
);

exit($braki > 0 ? 2 : 0);
