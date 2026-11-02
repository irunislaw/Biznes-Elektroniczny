from main import parse_product_urls, parse_subcategory_urls

# Uproszczony HTML w strukturze motywu classic PrestaShopa, takiej jak w sklepie źródłowym.
CATEGORY_TREE_HTML = """
<ul class="category-sub-menu">
  <li data-depth="0">
    <a href="https://gitara-sklep.pl/333-koncertowe">Koncertowe</a>
    <div class="collapse">
      <ul class="category-sub-menu">
        <li data-depth="1"><a href="https://gitara-sklep.pl/350-zagniezdzona">Zagnieżdżona</a></li>
      </ul>
    </div>
  </li>
  <li data-depth="0"><a href="https://gitara-sklep.pl/340-sopranowe">Sopranowe</a></li>
</ul>
"""

PRODUCT_A = "https://gitara-sklep.pl/koncertowe/1765-ukulele-koncertowe-se-20c-nt-ever-play.html"
PRODUCT_B = "https://gitara-sklep.pl/koncertowe/1770-ukulele-koncertowe-koa-24c-segovia.html"


def product_list_html(product_urls, next_page_url=None):
    thumbnails = "".join(f'<a href="{url}" class="thumbnail product-thumbnail"><img></a>' for url in product_urls)
    pagination = f'<a rel="next" href="{next_page_url}" class="next">Następna</a>' if next_page_url else ""
    return f"<div class='products'>{thumbnails}</div><nav class='pagination'>{pagination}</nav>"


def test_subcategories_only_from_first_level():
    assert parse_subcategory_urls(CATEGORY_TREE_HTML) == [
        "https://gitara-sklep.pl/333-koncertowe",
        "https://gitara-sklep.pl/340-sopranowe",
    ]


def test_leaf_category_has_no_subcategories():
    assert parse_subcategory_urls(product_list_html([PRODUCT_A])) == []


def test_products_with_next_page():
    html = product_list_html([PRODUCT_A, PRODUCT_B], next_page_url="https://gitara-sklep.pl/333-koncertowe?page=2")

    assert parse_product_urls(html) == ([PRODUCT_A, PRODUCT_B], True)


def test_products_on_last_page():
    assert parse_product_urls(product_list_html([PRODUCT_A])) == ([PRODUCT_A], False)


def test_empty_product_list():
    assert parse_product_urls(product_list_html([])) == ([], False)
