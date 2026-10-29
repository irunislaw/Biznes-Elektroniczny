from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    description: str
    price_gross: Decimal
    sale_price_gross: Decimal | None = None
    vat_rate_percent: Decimal | None = None
    weight: Decimal | None = None
    attributes: dict[str, str] = {}
    url: HttpUrl
    category_path: list[str] = Field(min_length=1)
    id_category_default: int
    image_urls: list[HttpUrl] = Field(min_length=1)
