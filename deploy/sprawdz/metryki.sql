-- Etap 1: metryki danych sklepu

-- Metryka 1: Liczba produktow: aktywne produkty (>= 1000)
SELECT
    COUNT(*) AS aktywne_produkty,
    IF(COUNT(*) >= 1000, 'OK', 'BŁĄD') AS status
FROM ps_product
WHERE active = 1;

-- Metryka 2A: Kategorie i podkategorie: lista kategorii glownych
SELECT
    k.*,
    IF(niepuste_podkategorie >= 2 AND niepuste_podkategorie = podkategorie, 'OK', 'BŁĄD') AS status
FROM (
    SELECT
        l.name AS kategoria_glowna,
        COUNT(DISTINCT s.id_category) AS podkategorie,
        COUNT(DISTINCT IF(cp.id_product IS NULL, NULL, s.id_category)) AS niepuste_podkategorie,
        -- produkty z calej kategorii glownej, takze gdy nie ma podkategorii
        (SELECT COUNT(DISTINCT cp2.id_product)
            FROM ps_category d2
            JOIN ps_category_product cp2 ON cp2.id_category = d2.id_category
            WHERE d2.nleft BETWEEN m.nleft AND m.nright) AS produkty
    FROM ps_category m
    JOIN ps_category_lang l ON l.id_category = m.id_category
    LEFT JOIN ps_category s ON s.id_parent = m.id_category
    -- d = podkategoria i wszystkie kategorie pod nia
    LEFT JOIN ps_category d ON d.nleft BETWEEN s.nleft AND s.nright
    LEFT JOIN ps_category_product cp ON cp.id_category = d.id_category
    WHERE m.id_parent = (SELECT value FROM ps_configuration WHERE name = 'PS_HOME_CATEGORY')
        AND l.id_lang = (SELECT id_lang FROM ps_lang WHERE iso_code = 'pl')
    GROUP BY m.id_category, m.nleft, m.nright, l.name
) AS k;

-- Metryka 2B: Kategorie i podkategorie: >= 4 kategorie, kazda z >= 2 niepustymi podkategoriami, 0 pustych
SELECT
    COUNT(*) AS kategorie_glowne,
    MIN(niepuste_podkategorie) AS najmniej_niepustych,
    SUM(podkategorie - niepuste_podkategorie) AS puste_podkategorie,
    IF(COUNT(*) >= 4
        AND MIN(niepuste_podkategorie) >= 2
        AND SUM(podkategorie - niepuste_podkategorie) = 0, 'OK', 'BŁĄD') AS status
FROM (
    SELECT
        COUNT(DISTINCT s.id_category) AS podkategorie,
        COUNT(DISTINCT IF(cp.id_product IS NULL, NULL, s.id_category)) AS niepuste_podkategorie
    FROM ps_category m
    LEFT JOIN ps_category s ON s.id_parent = m.id_category
    -- d = podkategoria i wszystkie kategorie pod nia
    LEFT JOIN ps_category d ON d.nleft BETWEEN s.nleft AND s.nright
    LEFT JOIN ps_category_product cp ON cp.id_category = d.id_category
    WHERE m.id_parent = (SELECT value FROM ps_configuration WHERE name = 'PS_HOME_CATEGORY')
    GROUP BY m.id_category
) AS k;

-- Metryka 3: Kompletnosc rekordow: produkty bez nazwy, opisu, ceny lub zdjecia (0)
SELECT
    t.*,
    IF(bez_nazwy + bez_opisu + bez_ceny + bez_zdjecia = 0, 'OK', 'BŁĄD') AS status
FROM (
    SELECT
        SUM(COALESCE(l.name, '') = '') AS bez_nazwy,
        SUM(COALESCE(l.description, '') = '') AS bez_opisu,
        SUM(p.price <= 0) AS bez_ceny,
        SUM(i.id_product IS NULL) AS bez_zdjecia
    FROM ps_product p
    LEFT JOIN ps_product_lang l ON l.id_product = p.id_product
        AND l.id_lang = (SELECT id_lang FROM ps_lang WHERE iso_code = 'pl')
    LEFT JOIN (SELECT DISTINCT id_product FROM ps_image) i ON i.id_product = p.id_product
) AS t;

-- Metryka 4A: Maksymalny stan magazynowy: stan kazdego produktu i wariantu od 0 do 10
SELECT
    MIN(quantity) AS najnizszy_stan,
    MAX(quantity) AS najwyzszy_stan,
    IF(MIN(quantity) >= 0 AND MAX(quantity) <= 10, 'OK', 'BŁĄD') AS status
FROM ps_stock_available;

-- Metryka 4B: Produkty niedostepne: produkty ze stanem 0 (5-20%)
SELECT
    SUM(quantity = 0) AS produkty_ze_stanem_0,
    COUNT(*) AS produkty,
    ROUND(100 * AVG(quantity = 0), 1) AS procent,
    IF(100 * AVG(quantity = 0) BETWEEN 5 AND 20, 'OK', 'BŁĄD') AS status
FROM ps_stock_available
WHERE id_product_attribute = 0;
