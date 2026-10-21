import time
from datetime import datetime
from urllib import robotparser

import requests


class ShopClient:
    def __init__(self, user_agent, shop_url, requests_per_second):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        self.rp = robotparser.RobotFileParser()
        self.rp.set_url(shop_url + "/robots.txt")
        self.rp.read()

        self.user_agent = user_agent
        self.interval = 1 / requests_per_second
        self.last_request = 0

    def get(self, url):
        if not self.rp.can_fetch(self.user_agent, url):
            print(f"Strona: {url} zablokowana przez robots.txt")
            return None

        wait = self.interval - (time.time() - self.last_request)
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.time()
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}: {url}")
        page = self.session.get(url)

        if page.status_code != 200:
            print(f"{page.status_code}: {url}")
            return None

        return page
