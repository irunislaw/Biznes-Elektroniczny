"""Wspólne elementy testów: sztuczny klient zamiast ShopClient, więc testy nie łączą się ze sklepem."""

from types import SimpleNamespace


class FakeClient:
    """Zastępuje ShopClient: zwraca przygotowane odpowiedzi i zapamiętuje pobierane adresy."""

    def __init__(self, responses):
        self.responses = responses
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        content = self.responses.get(url)
        return SimpleNamespace(content=content) if content is not None else None
