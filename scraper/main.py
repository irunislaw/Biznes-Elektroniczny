import json
import time
from datetime import datetime
from urllib import robotparser

import config
import requests
from bs4 import BeautifulSoup

links = set()
page_counter = 1

# Ustawienie parsera na plik robots.txt
rp = robotparser.RobotFileParser()
rp.set_url(config.SHOP_URL + "/robots.txt")
rp.read()

session = requests.Session()
session.headers.update({"User-Agent": config.USER_AGENT})

last_request = 0

while True:
    page_url = config.SCRAPER_START_URL + f"?page={page_counter}"

    # Sprawdzenie czy robots.txt pozwala na scrapowanie strony
    if not rp.can_fetch(config.USER_AGENT, page_url):
        print(f"Strona: {page_url} zablokowana przez robots.txt")
        break

    wait = (1 / config.REQUESTS_PER_SECOND) - (time.time() - last_request)
    if wait > 0:
        time.sleep(wait)
    last_request = time.time()
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}: {page_url}")
    page = session.get(page_url)
    soup = BeautifulSoup(page.content, "html.parser")

    links_HTML = soup.select("a.product-thumbnail")

    for link in links_HTML:
        links.add(link.get("href"))

    # Jeżeli nie ma przycisku przeniesienia do następnej strony to kończymy scrapowanie
    if not soup.select("a[rel='next']"):
        break

    page_counter += 1

with open(config.SAVE_PATH, "w", encoding="utf-8") as file:
    json.dump(list(links), file)
