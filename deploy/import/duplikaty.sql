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

-- warianty: ten sam produkt z tym samym zestawem wartości cech
SELECT id_product, wartosci, COUNT(*) AS ile
FROM (
    SELECT pa.id_product, GROUP_CONCAT(pac.id_attribute ORDER BY pac.id_attribute) AS wartosci
    FROM ps_product_attribute pa
    JOIN ps_product_attribute_combination pac ON pac.id_product_attribute = pa.id_product_attribute
    GROUP BY pa.id_product, pa.id_product_attribute
) AS w
GROUP BY id_product, wartosci
HAVING COUNT(*) > 1;

-- cechy wariantów i ich wartości o tej samej nazwie
SELECT name, COUNT(*) AS ile
FROM ps_attribute_group_lang
WHERE id_lang = 1
GROUP BY name
HAVING COUNT(*) > 1;

SELECT a.id_attribute_group, al.name, COUNT(*) AS ile
FROM ps_attribute a
JOIN ps_attribute_lang al
  ON al.id_attribute = a.id_attribute AND al.id_lang = 1
GROUP BY a.id_attribute_group, al.name
HAVING COUNT(*) > 1;

SELECT (SELECT COUNT(*) FROM ps_product)  AS produkty,
       (SELECT COUNT(*) FROM ps_category) AS kategorie,
       (SELECT COUNT(*) FROM ps_image)    AS zdjecia,
       (SELECT COUNT(*) FROM ps_specific_price) AS promocje,
       (SELECT COUNT(*) FROM ps_product_attribute) AS warianty;