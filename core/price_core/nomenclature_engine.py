import json
import math
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

# Persist settings for the Zenon region we scrape.
COOKIES = {
    "_framework_rails_session": "VkQzNGxtZUUzbkNEdDgxeDVrdjF0OWlGdWltRHZSdXd5eTBSZ2tRRjJKQ3g0SUNPNStDNWxjWGZYZlJ0dWVEalRaSktsc1lIUjlVQkFKUmxTajlmVWFXVzBPNVJtaFVDM0tXRytGcFNqNUNZd1orTmlLVlBwYkZIR1kzSkErYmZ4ck41QmVKTTh1c0owOGhlbXJuWUFzUVJrdzQ4dS9zY0NtMmFUckE3cjdRUUQrNWJDT3lORDhMK0F5NzNDbE9aeWNaTU81bXBDS1YrV2piU0ZWTzdFWC9LQ0FCNjNnMVNiRXUwYVBUMGpsL2F5RWdiNlkybXNNWS9CN3U5alY1dkNrejNiYk9yYkFhRVMvZVBXcngvSDIvNW0wN2pyMjE2aHZnRFFiUDY1ei9qR3NZN21uY25PTUQvQ09FTW5SS2Z0VVhwZUZzUWU3bjk3L1RzNVFYQWFxMk5pSEhVMnNDUzV4OW0yM1Yrc3hnPS0ta3c0QnJwTENneVNDYlcrUkc5WEZwdz09--fbfc23f024912f365dbd768aab2576d9b3c57e3d",
    "_ym_d": "1755172114",
    "_ym_isad": "1",
    "_ym_uid": "1741084822176864213",
    "agreement": "true",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36",
    "Accept-Language": "ru,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "nomenclature.json"


@dataclass
class MaterialItem:
    name: str
    buy_unit: str
    buy_size: str
    sale_count: float
    buy_price: int
    sale_unit: str
    sale_price: int
    url: str

    @classmethod
    def from_dict(cls, raw: dict) -> "MaterialItem":
        return cls(
            name=raw["name"],
            buy_unit=raw.get("buy_unit", ""),
            buy_size=raw.get("buy_size", ""),
            sale_count=float(raw.get("sale_count", 0)),
            buy_price=int(raw.get("buy_price", 0)),
            sale_unit=raw.get("sale_unit", ""),
            sale_price=int(raw.get("sale_price", 0)),
            url=raw["url"],
        )

    def to_dict(self) -> dict:
        return asdict(self)


def load_items(path: Path | str = DATA_FILE) -> List[MaterialItem]:
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return [MaterialItem.from_dict(entry) for entry in payload]


def save_items(items: Iterable[MaterialItem], path: Path | str = DATA_FILE) -> None:
    path = Path(path)
    payload = [item.to_dict() for item in items]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def calc_sale_price(purchase_price: float, sale_units: float) -> int:
    if not sale_units:
        return 0
    raw_price = (purchase_price / sale_units) * 1.1
    return int(math.ceil(raw_price / 10.0) * 10)


def fetch_title_and_price(url: str, *, session: Optional[requests.Session] = None) -> tuple[Optional[str], Optional[int]]:
    client = session or requests
    response = client.get(url, headers=HEADERS, cookies=COOKIES, timeout=20)
    if response.status_code != 200:
        return None, None
    soup = BeautifulSoup(response.text, "html.parser")
    title_node = soup.select_one("h1") or soup.select_one(".product__title")
    title = title_node.get_text(strip=True) if title_node else None
    price_tags = [tag.get_text(strip=True) for tag in soup.select(".rub")]
    prices: List[int] = []
    for text in price_tags:
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            prices.append(int(digits))
    return title, max(prices) if prices else None


def update_sale_price(item: MaterialItem) -> None:
    item.sale_price = calc_sale_price(item.buy_price, item.sale_count)


def refresh_item(item: MaterialItem, *, session: Optional[requests.Session] = None) -> bool:
    title, price = fetch_title_and_price(item.url, session=session)
    if price is None:
        return False
    if title:
        item.name = title
    item.buy_price = price
    update_sale_price(item)
    return True


def refresh_items(items: Iterable[MaterialItem], *, session: Optional[requests.Session] = None) -> List[MaterialItem]:
    updated: List[MaterialItem] = []
    for item in items:
        refreshed = refresh_item(item, session=session)
        if refreshed:
            updated.append(item)
    return updated


def search_items(items: Iterable[MaterialItem], query: str) -> List[MaterialItem]:
    q = query.lower().strip()
    if not q:
        return []
    return [item for item in items if q in item.name.lower()]


__all__ = [
    "COOKIES",
    "HEADERS",
    "DATA_FILE",
    "MaterialItem",
    "calc_sale_price",
    "fetch_title_and_price",
    "load_items",
    "save_items",
    "refresh_item",
    "refresh_items",
    "search_items",
    "update_sale_price",
]
