import logging
import time
from urllib import robotparser

import requests

logger = logging.getLogger(__name__)


class ShopClient:
    def __init__(self, user_agent, shop_url, requests_per_second, max_attempts):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        self.user_agent = user_agent
        self.interval = 1 / requests_per_second
        self.last_request = 0
        self.max_attempts = max_attempts

        self.watch_requests_limit()

        self.rp = robotparser.RobotFileParser()
        robots_url = shop_url + "/robots.txt"
        logger.info("GET %s", robots_url)
        robots = self.session.get(robots_url)
        self.rp.parse(robots.content.decode("utf-8").splitlines())
        logger.info("%s %s", robots.status_code, robots_url)

    def watch_requests_limit(self):
        wait = self.interval - (time.time() - self.last_request)
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.time()

    def get(self, url):
        if not self.rp.can_fetch(self.user_agent, url):
            logger.warning("Strona %s zablokowana przez robots.txt", url)
            return None

        for attempt in range(1, self.max_attempts + 1):
            if attempt > 1:
                time.sleep(2 ** (attempt - 1))
            self.watch_requests_limit()
            logger.info("GET %s (próba %d)", url, attempt)
            try:
                page = self.session.get(url, timeout=10)
            except requests.exceptions.RequestException as e:
                logger.warning("Błąd w pobraniu strony %s: %s", url, e)
                continue
            logger.info("%s %s", page.status_code, url)

            if page.status_code in (429, 500, 502, 503, 504):
                logger.info("Status code: %s: %s", page.status_code, url)
                continue

            elif page.status_code == 200:
                return page

            break

        logger.warning("Nie udało się pobrać %s", url)
        return None
