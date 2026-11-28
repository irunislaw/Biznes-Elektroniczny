# Różnice w układzie: sklep źródłowy a nasz sklep (Classic)

Materiał na planowanie sprintu 3 (BE-26). Na jego podstawie powstaną tickety zmian wyglądu.

**Zrzuty:** `zrodlo/` to https://gitara-sklep.pl, `nasz/` to nasz sklep po `make init` (motyw `gitara`, na razie bez zmian względem Classic). Pliki `komputer-*` mają szerokość 1440 px, `360-*` to telefon. Strony: `1-glowna`, `2-kategoria` (Ukulele › Sopranowe), `3-produkt` (UKU-701S NT Ever Play), `4-koszyk`. Odświeżenie zrzutów: `make wyglad`.

**Najważniejsze:** sklep źródłowy też działa na motywie Classic, tylko w starszej wersji (PrestaShop 1.7). Szkielet stron jest więc ten sam: szerokość treści (1110 px), nagłówek z paskiem kontaktu, siatka 3 produktów w kategorii, karta produktu z galerią po lewej i zakładkami Opis/Szczegóły, koszyk z podsumowaniem po prawej i stopka w 4 kolumnach. Większość różnic to bloki modułów, które są włączone albo wyłączone, ich kolejność i kilka poprawek CSS. Nie trzeba przebudowywać szablonów.

**Skala szacunków:** godziny pracy jednej osoby razem ze sprawdzeniem na obu szerokościach. Zmiany robimy tylko w repozytorium: CSS w `shop/themes/gitara/assets/css/custom.css`, ustawienia modułów i konfiguracji w skrypcie w `deploy/config/` uruchamianym przez `make init`. W panelu nic nie klikamy, bo tego nie będzie u prowadzącego.

Kolumna „Jak” oznacza: **CSS** to `custom.css`, **konfiguracja** to skrypt w `deploy/config/` (hooki, moduły, `ps_configuration`), **szablon** to nadpisany plik `.tpl` w motywie.

## 1. Nagłówek i menu

| # | Źródło | Nasz sklep | Jak | Szacunek |
|---|---|---|---|---|
| N1 | Menu ma jedną pozycję „Katalog produktów”, a wyszukiwarka jest w tym samym wierszu, po prawej. | Pięć kategorii głównych w rzędzie, więc wyszukiwarka spada do drugiego wiersza pod menu. | Do wyboru: (a) menu jak w źródle, z jedną pozycją, w ustawieniach `ps_mainmenu`; (b) zostają kategorie, a CSS ustawia menu i wyszukiwarkę w jednym wierszu. Wariant (b) jest wygodniejszy dla klienta, ale BE-19 celowo wprowadził kategorie w menu. | 2 h |
| N2 | Telefon: hamburger, logo, konto, koszyk, wyszukiwarka pod spodem. | To samo. | Bez zmian. | 0 |

## 2. Lista produktów (kategoria)

| # | Źródło | Nasz sklep | Jak | Szacunek |
|---|---|---|---|---|
| L1 | W lewej kolumnie jest tylko blok bieżącej kategorii. | Drzewo kategorii od „Strona główna” oraz bloki „Marki” i „Dostawcy” (puste: „Brak marki”, „Brak dostawców”). | Konfiguracja: drzewo `ps_categorytree` od bieżącej kategorii, `ps_brandlist` i `ps_supplierlist` odpięte z lewej kolumny. | 1,5 h |
| L2 | Telefon: lewej kolumny nie ma, produkty są od razu pod tytułem kategorii. | Telefon: trzy bloki lewej kolumny stoją przed produktami, czyli ok. jednego ekranu przewijania. | CSS: ukryć `#left-column` na kategorii poniżej 768 px. | 1 h |
| L3 | 16 produktów na stronę. | 12 produktów na stronę. | Konfiguracja: `PS_PRODUCTS_PER_PAGE`. | 0,5 h |
| L4 | Na miniaturze nie ma znaczków „Nowy” ani serduszka ulubionych. | Każdy produkt ma „NOWY” (wszystkie zostały dodane niedawno importem) i serduszko z `blockwishlist`. | Konfiguracja: `PS_NB_DAYS_NEW_PRODUCT` = 0 oraz wyłączenie `blockwishlist` albo ukrycie serduszka w CSS. Usuwa też problem P3. | 1 h |
| L5 | Telefon: brak okruszków (Strona główna / Ukulele / …). | Okruszki są widoczne. | CSS, opcjonalnie. | 0,5 h |
| L6 | Siatka 3 kolumn, sortowanie, licznik produktów, stronicowanie, karta miniatury. | To samo. | Bez zmian. | 0 |

## 3. Karta produktu

| # | Źródło | Nasz sklep | Jak | Szacunek |
|---|---|---|---|---|
| P1 | Pod przyciskiem „Udostępnij” nic nie ma. | Blok `blockreassurance` z tekstem demo („Security policy (edit with the Customer Reassurance module)”). Ten sam blok jest w koszyku. | Konfiguracja: wyłączyć moduł. | 0,5 h |
| P2 | Lista specyfikacji w opisie jest pogrubiona i bez punktorów. | Punktory stoją w osobnej linii nad tekstem, bo opis ma `<li><h3>…</h3></li>`, a Classic 2.x wyświetla `h3` jako blok z marginesami. | CSS dla `.product-description li h3`. | 1 h |
| P3 | Telefon: strona mieści się w 360 px. | Telefon: strona ma 373 px szerokości i przewija się w bok, bo serduszko obok „Dodaj do koszyka” wystaje poza ekran. | Znika razem z serduszkiem (L4). Gdy serduszko zostaje, poprawka w CSS. | 0 albo 1 h |
| P4 | Pod opisem jest blok „Zobacz także” z 3 produktami. | Sekcja „Komentarze (0)” z napisem „Na razie nie dodano żadnej recenzji” oraz karuzela „16 innych produktów w tej samej kategorii”. | Konfiguracja: odpiąć `productcomments`, ustawić blok produktów z tej samej kategorii. | 1,5 h |
| P5 | Galeria z miniaturami pod zdjęciem, nazwa, cena, ilość, przycisk, udostępnianie, zakładki Opis/Szczegóły. | To samo. | Bez zmian. | 0 |

## 4. Koszyk

| # | Źródło | Nasz sklep | Jak | Szacunek |
|---|---|---|---|---|
| K1 | Lista produktów po lewej, podsumowanie i przycisk po prawej. Na telefonie jedno pod drugim. | To samo, na obu szerokościach. | Bez zmian. | 0 |
| K2 | Pod podsumowaniem nic nie ma. | Blok `blockreassurance` z tekstem demo. | Załatwia to P1. | 0 |
| K3 | Przycisk „Realizuj zamówienie” ma szerokość tekstu. | „Przejdź do realizacji zamówienia” na całą szerokość kolumny. | Tekst wynika z tłumaczenia nowszej wersji PrestaShop. CSS, opcjonalnie. Zrobione: tłumaczenie w `uklad.php` i CSS. | 0,5 h |

## 5. Stopka

| # | Źródło | Nasz sklep | Jak | Szacunek |
|---|---|---|---|---|
| S1 | Cztery kolumny: Produkty, Nasza firma, Twoje konto, Informacja o sklepie. Na telefonie rozwijane sekcje. | To samo. | Bez zmian. Linki w „Nasza firma” różnią się celowo, bo strony CMS są nasze (BE-30). | 0 |
| S2 | Newsletter wyrównany do lewej, z małym napisem. | Newsletter wyśrodkowany, z dużym nagłówkiem (styl Classic 2.x). | CSS, opcjonalnie. | 1 h |
| S3 | Nad newsletterem jest link „Katalog produktów”. | Brak. | Konfiguracja albo szablon. Opcjonalnie, mała wartość. | 1 h |

## 6. Strona główna

Tego obszaru nie ma w zadaniu, ale jest na zrzutach i rzuca się w oczy najbardziej.

| # | Źródło | Nasz sklep | Jak | Szacunek |
|---|---|---|---|---|
| G1 | Kolejność: slider → „Popularne produkty” (8 sztuk, `ps_featuredproducts`) z linkiem „Wszystkie produkty” → baner z godzinami otwarcia → długi tekst o sklepie. | Slider → baner → tekst → „Nowe produkty” (8 sztuk). | Konfiguracja: kolejność modułów w `displayHome` i produkty w kategorii Strona główna dla `ps_featuredproducts`. | 3 h |

## 7. Wygląd ogólny (poza układem)

| # | Źródło | Nasz sklep | Jak | Szacunek |
|---|---|---|---|---|
| O1 | Krój Noto Sans (Classic z PrestaShop 1.7), mniejsze nagłówki. | Krój Manrope (Classic 2.2), większe nagłówki. | CSS z fontem z Google Fonts albo z plików w motywie. Opcjonalnie: PDF nie wymaga typografii, ale to tani sposób, żeby strony wyglądały „tak samo”. | 1,5 h |

## 8. Treść i dane (nie układ, osobne tickety)

Te różnice nie wynikają z motywu, więc nie da się ich usunąć w CSS. Są jednak najbardziej widoczne na zrzutach i bez nich nawet idealny układ będzie wyglądał inaczej.

- **Logo:** u nas jest domyślne „my store”. Logo sklepu źródłowego jest wyższe, więc zmienia też wysokość nagłówka.
- **Slider i baner na stronie głównej:** u nas zostały treści demo instalatora („Sample 3”, „20% off on clothes”).
- **Opis i zdjęcie kategorii:** w źródle są w ramce nad listą produktów. U nas jest tylko nazwa, bo import ich nie przenosi.
- **Krótki opis produktu** (w źródle pod ceną, np. „+ tabela chwytów, + poradnik…”): scraper go nie zbiera, a import nie wysyła.
- **Promocje:** w źródle są znaczki „-19,00 zł” i przekreślone ceny. `results.json` ma 302 produkty z `sale_price_gross`, ale import nie tworzy cen promocyjnych. Po dodaniu ich do importu znaczki pokażą się same, bez zmian w motywie.
- **Zdjęcie główne:** przy części produktów jest inne niż w źródle, np. UKU-701S NT. Trzeba sprawdzić, które zdjęcie import ustawia jako główne.

## Propozycja: jak blisko celujemy

PDF wymaga układu „identycznego lub zbliżonego”, bez kolorystyki. Proponuję poziom 1 jako zakres sprintu 3.

**Poziom 1, układ zbliżony (proponowany), ok. 12 h + 2 h na sprawdzenie:** N1, L1, L2, L3, L4, P1, P2, P4, G1, a P3 rozwiązuje się razem z L4. Po tych zmianach każda z czterech stron ma te same bloki w tej samej kolejności co źródło, na komputerze i na telefonie. Zostają różnice w typografii i detalach, których PDF nie wymaga.

**Poziom 2, układ prawie identyczny, ok. 5 h więcej:** poziom 1 oraz L5, K3, S2, S3, O1. Strony wyglądają na pierwszy rzut oka tak samo, ale punktów od tego nie przybywa.

**Poziom 3, wierna kopia każdego detalu: odradzam.** Pliki CSS źródła pochodzą ze starszego Classic i nie pasują do szablonów Classic 2.x. Przeniesienie ich albo odtwarzanie piksel po pikselu to kilkadziesiąt godzin poprawiania kolizji, bez dodatkowych punktów.

Niezależnie od poziomu warto zaplanować tickety z sekcji 8, zwłaszcza logo, slider i promocje. Bez nich porównanie ze źródłem wypadnie słabo nawet przy dobrym układzie.

Decyzja należy do zespołu na planowaniu sprintu 3. Każdy wiersz z sekcji 1–7 to kandydat na osobny ticket albo na podzadanie jednego ticketu „Układ: poziom 1”.

## BE-33: co zostało usunięte

CSS jest w `shop/themes/gitara/assets/css/custom.css`, a ustawienia modułów w `deploy/config/uklad.php`
i `deploy/config/cms.php`, które uruchamia `make init`. Jeden szablon jest nadpisany, bo linków w stopce nie da się
zmienić CSS: `shop/themes/gitara/modules/ps_customeraccountlinks/ps_customeraccountlinks.tpl` (kopia z Classic
w motywie potomnym, Classic bez zmian, wymóg D1).
**Zrzuty:** `przed/` to stan przed BE-33, `nasz/` to stan po nim, `zrodlo/` to sklep źródłowy.

Układy stron (lewa kolumna albo pełna szerokość) były już takie jak w źródle: kategorie, nowe produkty,
promocje i kontakt mają lewą kolumnę, reszta stron ma pełną szerokość. Zmieniła się zawartość nagłówka
i lewej kolumny.

| Obszar | Wiersze | Zmiana | Gdzie |
|---|---|---|---|
| Nagłówek | N1 (a) | W menu jest jedna pozycja „Katalog produktów” (link do kategorii głównej), jak w źródle. Menu i wyszukiwarka stoją w jednym wierszu. | konfiguracja i CSS |
| Nagłówek, telefon | N2 | Bez zmian. | |
| Lewa kolumna | L1 | Drzewo zaczyna się od bieżącej kategorii („Sopranowe” na liście sopranowych). Bloki „Marki” i „Dostawcy” są odpięte. | konfiguracja |
| Telefon | L2, L5 | Bez drzewa kategorii i bez okruszków na wszystkich stronach (w źródle `hidden-sm-down`), więc produkty są od razu pod tytułem. | CSS |
| Lista produktów | L3 | 16 produktów na stronę. | konfiguracja |
| Kafelek | L4 | `blockwishlist` jest wyłączony, więc nie ma serduszka. Znaczek „Nowy” jest ukryty w CSS, bo `PS_NB_DAYS_NEW_PRODUCT` = 0 wyczyściłby stronę „Nowe produkty”. | konfiguracja i CSS |
| Karta produktu | P1, P2, P3 | Bez bloku demo `blockreassurance` (także w koszyku, K2). Specyfikacja to pogrubione linie bez punktorów. Strona mieści się w 360 px. | CSS |
| Stopka | S2 | Newsletter przy lewej krawędzi, z małym napisem. | CSS |
| Stopka | S1 | „Nasza firma”: najpierw Regulamin, O sklepie, Formy płatności jak w źródle, potem Dostawa i Polityka prywatności (strony wymagane u nas, w źródle ich nie ma), Kontakt, Mapa strony. „Twoje konto” dla gościa: Dane osobowe, Zamówienia, Korekty płatności, Adresy jak w źródle (każdy link prowadzi przez logowanie). Tytuły „Produkty” i „Nasza firma” 18 px, dane sklepu 16 px, telefon i e-mail szare, odstępy jak w źródle. Wszystkie linki zwracają 200 albo przekierowują na logowanie. | `cms.php`, szablon `modules/ps_customeraccountlinks` w motywie (kopia z Classic, zmieniona tylko gałąź gościa) i CSS |
| Strona główna | G1 | Pod sliderem „Popularne produkty” (8 produktów przypiętych do kategorii „Strona główna”, po 2 z pierwszych kategorii menu) z linkiem „Wszystkie produkty”, potem obraz sklepu z godzinami otwarcia (`ps_banner`, na telefonie ukryty jak w źródle) i tekst o sklepie z podpisem zespołu (`cms/strona-glowna.html`), a pod nim drugi raz menu z linkiem „Katalog produktów” (`ps_mainmenu`, tylko na komputerze, jak w źródle). „Nowe produkty”, „Promocje” i „Najczęściej kupowane” są odpięte od strony głównej. Kafelki produktów mają cień jak w źródle. | konfiguracja i CSS |
| Nagłówek | sekcja 8 | Logo sklepu zamiast „my store”. | konfiguracja |
| Katalog produktów | K0 | Kategoria główna nazywa się „Katalog produktów Gitara No.1”, ma adres `/2-katalog-produktow-gitara-no1` (stary `/2-strona-glowna` przekierowuje) i obrazek z `shop/themes/gitara/assets/katalog-produktow.jpg`. Bez bloku „Podkategorie” na tej stronie. | konfiguracja i CSS |
| Wszystkie kategorie | — | Tytuł w nagłówku kategorii 22 px, tytuł drzewa w lewej kolumnie 15 px pogrubiony (jak w Classic 1.7), obrazek kategorii przy prawej krawędzi. | CSS |
| Cały sklep | — | Czcionka Noto Sans (jak w Classic z PrestaShop 1.7) zamiast Manrope. Pliki są w motywie (`assets/fonts`, licencja OFL), nie z Google Fonts. | CSS |

Test e2e koszyka przechodzi teraz do kategorii linkiem „Katalog produktów” z nagłówka, a nie linkiem
„Wszystkie nowe produkty” ze strony głównej (sekcja „Nowe produkty” jest odpięta). Link z nagłówka jest na każdej stronie.

Po ponownym imporcie (`deploy/import/import.py`) w menu znów będą kategorie główne, dopóki nie uruchomi się `make init`.

Produkty na stronie głównej `uklad.php` przypina tylko wtedy, gdy kategoria „Strona główna” jest pusta,
więc wybór zmieniony w panelu (Katalog > Produkty > Powiązania) zostaje. Import przy aktualizacji nie zmienia
kategorii produktów, więc przypisanie zostaje też po ponownym imporcie. Te same produkty widać na stronie
„Katalog produktów”.

Logo i obraz sklepu są w motywie (`shop/themes/gitara/assets/logo.png` i `baner.webp`). `uklad.php` kopiuje
je tam, gdzie szuka ich PrestaShop (`img/` i katalog `ps_banner`). Żeby je podmienić, wystarczy zamienić pliki
i uruchomić `make init`.

Zostaje poza BE-33: zdjęcia w sliderze (dziś demo „SAMPLE”) oraz komentarze i „Zobacz także” na karcie produktu (P4).
