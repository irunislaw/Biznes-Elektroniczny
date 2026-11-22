# Lighthouse przed i po zmianach układu (BE-33)

Pomiar ma pokazać, że zmiany układu z BE-33 nie pogorszyły wyników poniżej progów z S3-05.

**Próg z S3-05:** Accessibility ≥ 85 na każdej stronie, mobile i desktop. Przed zmianami nie spełnia go
karta produktu (76), patrz niżej.

**Jak mierzone:** Lighthouse 12.6.0 w kontenerze `playwright` (Chromium z obrazu Playwright, `--ignore-certificate-errors`
dla certyfikatu z `make certs`), sklep po `make init`, ustawienia domyślne: mobile z symulowanym dławieniem
albo `--preset=desktop`. Baner cookies jest widoczny, tak jak u nowego klienta. Strony i adresy są te same co
w zrzutach (`tests/zrzuty/wyglad.spec.ts`).

Performance na mobile różni się między przebiegami nawet o 10 punktów, dlatego jest medianą z 3 przebiegów.
Pozostałe kategorie są stałe i pochodzą z jednego przebiegu.

Kolejność kolumn: Performance / Accessibility / Best Practices / SEO.

## Przed (2026-11-16, master 699da05)

| Strona | Mobile | Desktop |
|---|---|---|
| Strona główna | 75 / 97 / 96 / 85 | 98 / 94 / 100 / 85 |
| Kategoria (Sopranowe) | 66 / 93 / 96 / 85 | 98 / 93 / 100 / 85 |
| Produkt (UKU-701S NT) | 70 / 76 / 89 / 85 | 99 / 76 / 93 / 85 |
| Koszyk | 73 / 96 / 93 / 50 | 95 / 96 / 96 / 50 |

Przebiegi performance mobile: główna 64, 76, 75; kategoria 68, 56, 66; produkt 70, 71, 70; koszyk 70, 74, 73.

Skąd niższe wyniki (już przed zmianami, nie przez BE-33):

- **Produkt, accessibility 76 (poniżej progu).** Wynik to ważona suma audytów: z łącznej wagi 214
  nie przechodzi 51. Każdy audyt odejmuje całą swoją wagę, niezależnie od liczby błędnych elementów:

  | Audyt | Waga | Przyczyna | Jak poprawić |
  |---|---|---|---|
  | `aria-required-children` | 10 | Zakładki Opis/Szczegóły: `<ul role="tablist">` ma dzieci `<li>` bez roli. | Szablon: `role="presentation"` na `li.nav-item` w bloku `product_tabs`. Jedna zmiana usuwa wszystkie trzy błędy (27 z 51). |
  | `aria-required-parent` | 10 | `<a role="tab">` nie jest bezpośrednio w `tablist`, bo w środku jest `<li>`. | jak wyżej |
  | `listitem` | 7 | `<li>` nie ma nad sobą listy, bo `ul` ma rolę `tablist`. | jak wyżej |
  | `button-name` | 10 | Przyciski +/− ilości (`bootstrap-touchspin`) nie mają tekstu. Wstawia je JS z Classic. | JS w motywie: `aria-label` „Zwiększ ilość” / „Zmniejsz ilość”. |
  | `target-size` | 7 | Te same przyciski +/− są mniejsze niż 24 × 24 px. | CSS w `custom.css`. |
  | `color-contrast` | 7 | Kolor główny Classic (#24b9d7) na białym tle: znaczek „Nowy”, cena, przycisk, zakładki, nazwy w karuzeli. Do tego `li h3` w opisie. | Wymaga zmiany koloru głównego, poza zakresem BE-33. |

  Po samej poprawce zakładek wynik wynosi (214 − 24) / 214 ≈ **89**. Po dodaniu przycisków +/− wynosi
  (214 − 7) / 214 ≈ **97**.
- **SEO 85 wszędzie:** brak `meta-description` i jeden link bez adresu (`crawlable-anchors`).
- **Koszyk, SEO 50:** do tego `is-crawlable`, bo koszyk ma `noindex`. Tak ma być.
- **Performance mobile:** LCP 3,6–6,3 s i TBT 350–820 ms. To wynik serwera deweloperskiego w Dockerze i JS
  z Classic, nie samego układu.

## Po (2026-11-22, 431b5a3)

| Strona | Mobile | Desktop |
|---|---|---|
| Strona główna | 84 / 97 / 96 / 92 | 97 / 97 / 100 / 92 |
| Kategoria (Sopranowe) | 80 / 96 / 96 / 92 | 98 / 96 / 100 / 92 |
| Produkt (UKU-701S NT) | 82 / 97 / 93 / 92 | 98 / 97 / 96 / 92 |
| Koszyk | 84 / 96 / 100 / 58 | 99 / 96 / 100 / 58 |

Przebiegi Performance mobile: główna 84, 88, 76; kategoria 79, 84, 80;
produkt 76, 83, 82; koszyk 83, 84, 84.

Główna, kategoria i produkt przekroczyły próg Accessibility 85 w obu trybach. Główna uzyskała
97 Performance na desktopie przy wymaganym minimum 60. Accessibility produktu wzrosło z 76 do 97.
Audyty struktury zakładek, nazw przycisków i rozmiaru obszarów klikania przeszły w obu trybach.
Na produkcie Lighthouse nadal zgłasza niewystarczający kontrast.
