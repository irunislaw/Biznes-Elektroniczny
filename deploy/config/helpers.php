<?php

// Wspólne funkcje skryptów konfiguracji. PrestaShop wczytuje skrypt wywołujący.

function ustaw(string $klucz, $wartosc): void
{
    if ((string) Configuration::get($klucz) === (string) $wartosc) {
        return;
    }
    if (!Configuration::updateValue($klucz, $wartosc)) {
        throw new RuntimeException("Nie udalo sie ustawic $klucz");
    }
}

// Kopiuje tylko zmieniony plik i ustawia właściciela wymaganego przez sklep.
// Zwraca true, gdy skopiował.
function skopiuj(string $skad, string $dokad): bool
{
    if (!is_file($skad)) {
        throw new RuntimeException("Brak pliku $skad");
    }
    if (is_file($dokad) && md5_file($skad) === md5_file($dokad)) {
        return false;
    }
    if (!copy($skad, $dokad)) {
        throw new RuntimeException("Nie udalo sie skopiowac $skad do $dokad");
    }
    chown($dokad, 'www-data');
    chgrp($dokad, 'www-data');
    return true;
}
