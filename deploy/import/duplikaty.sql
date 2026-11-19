SELECT reference, COUNT(*) AS ile
FROM ps_product
GROUP BY reference
HAVING COUNT(*) > 1;

SELECT c.id_parent, cl.link_rewrite, COUNT(*) AS ile
FROM ps_category c
JOIN ps_category_lang cl
  ON cl.id_category = c.id_category AND cl.id_lang = 1 AND cl.id_shop = 1
GROUP BY c.id_parent, cl.link_rewrite
HAVING COUNT(*) > 1;

SELECT id_product, COUNT(*) AS ile
FROM ps_specific_price
WHERE id_cart = 0
GROUP BY id_product
HAVING COUNT(*) > 1;

SELECT LOWER(TRIM(name)) AS marka, COUNT(*) AS ile
FROM ps_manufacturer
GROUP BY LOWER(TRIM(name))
HAVING COUNT(*) > 1;

SELECT (SELECT COUNT(*) FROM ps_product)  AS produkty,
       (SELECT COUNT(*) FROM ps_category) AS kategorie,
       (SELECT COUNT(*) FROM ps_image)    AS zdjecia,
       (SELECT COUNT(*) FROM ps_specific_price) AS promocje,
       (SELECT COUNT(*) FROM ps_manufacturer) AS marki;