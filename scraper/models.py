from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Brand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    logo_url: HttpUrl | None = None
    # Ścieżka względem scraper-results/, np. "images/brands/3.jpg" (uzupełnia download_images.py)
    logo_file: str | None = None


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    description: str
    price_gross: Decimal
    sale_price_gross: Decimal | None = None
    # Marka z karty produktu; None, gdy sklep nie podaje producenta
    brand: Brand | None = None
    vat_rate_percent: Decimal | None = None
    weight: Decimal | None = None
    attributes: dict[str, str] = {}
    url: HttpUrl
    category_path: list[str] = Field(min_length=1)
    id_category_default: int
    other_category_ids: list[int] = []
    image_urls: list[HttpUrl] = Field(min_length=1)
    # Ścieżki względem scraper-results/, np. "images/487-1.jpg" (uzupełnia download_images.py)
    image_files: list[str] = []
