from pydantic import BaseModel
from typing import Optional


class Asset(BaseModel):
    ticker: str
    name: str
    icon_url: str

class AssetRemove(BaseModel):
    ticker: str

class AssetQuote(Asset):
    price_usd: float
    direction: str  # "subindo", "caindo", "estável"

class HistoryPoint(BaseModel):
    date: str
    close: float

class Dividend(BaseModel):
    date: str
    amount: float

class Financials(BaseModel):
    market_cap: Optional[int]
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    target_price: Optional[float]
    recommendation: Optional[str]

class NewsItem(BaseModel):
    title: str
    link: str
    publisher: str
    summary: Optional[str] = ""
    provider_publish_time: str