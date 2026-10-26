import os

import config
from shop_client import ShopClient

URLS = [
    "https://gitara-sklep.pl/koncertowe/1589-ukulele-koncertowe-uk10s-harley-benton.html",
    "https://gitara-sklep.pl/mikrofonowe/3916-quad410-kabel-mikrofonowy-starquad-4-zyly-czarny-proel.html",
    "https://gitara-sklep.pl/skrzypce/2416-hv-300-skrzypce-44-futeral-smyczek-ars-nova.html",
    "https://gitara-sklep.pl/138-kostki",
]


def main():
    client = ShopClient(config.USER_AGENT, config.SHOP_URL, config.REQUESTS_PER_SECOND)

    counter = 1
    for url in URLS:
        page = client.get(url)
        if not page:
            print(f"Nie udało się pobrać: {url}")
            continue
        with open(
            os.path.join(config.FIXTURES_PATH, f"page-{counter}.html"), "wb"
        ) as file:
            file.write(page.content)
        counter += 1


if __name__ == "__main__":
    main()
