<?php

// Włącza motyw potomny z shop/themes/ (init.sh wcześniej kopiuje go do themes/ w sklepie).
// Motyw włączony tylko w panelu zniknąłby po make reset, dlatego robi to make init.

require_once '/var/www/html/config/config.inc.php';

use PrestaShop\PrestaShop\Core\Addon\Theme\ThemeManagerBuilder;

$themeName = 'gitara';

$context = Context::getContext();

if (!is_file(_PS_ALL_THEMES_DIR_ . $themeName . '/config/theme.yml')) {
    throw new RuntimeException("Brak motywu $themeName w katalogu themes");
}

if ($context->shop->theme_name === $themeName) {
    echo "Motyw ($themeName): OK, już włączony\n";
    return;
}

$themeManager = (new ThemeManagerBuilder($context, Db::getInstance()))->build();

// true: pomija sprawdzanie uprawnień pracownika, w CLI nikt nie jest zalogowany.
if (!$themeManager->enable($themeName, true)) {
    throw new RuntimeException("Nie udalo sie wlaczyc motywu $themeName (sprawdz config/theme.yml)");
}

echo "Motyw ($themeName): OK\n";
