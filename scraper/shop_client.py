import logging
import time
from urllib import robotparser

import requests

logger = logging.getLogger(__name__)


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
            logger.warning("Strona %s zablokowana przez robots.txt", url)
            return None

        wait = self.interval - (time.time() - self.last_request)
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.time()
        logger.info("GET %s", url)
        page = self.session.get(url)
        logger.info("%s %s", page.status_code, url)

        if page.status_code != 200:
            logger.warning("Status code: %s: %s", page.status_code, url)
            return None

        return page
