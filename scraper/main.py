import json
import time

import config
import requests
from bs4 import BeautifulSoup

links = []
page_counter = 1

while True:
    time_start = time.time()
    page = requests.get(config.SHOP_URL + f"?page={page_counter}")
    soup = BeautifulSoup(page.content, "html.parser")
    print(config.SHOP_URL + f"?page={page_counter}")

    if page.status_code != requests.codes.ok:
        break

    linksHTML = soup.find_all("a", "thumbnail", "product-thumbnail")
    if not linksHTML:
        break

    for link in linksHTML:
        links.append(link.get("href"))

    time_end = time.time()

    elapsed_time = time_end - time_start

    if elapsed_time < 0.5:
        time.sleep(0.5 - elapsed_time)

    page_counter += 1

with open("../scraper-results/result.json", "w") as file:
    json.dump(links, file)
