"""AssetService: normalização de ticker, 404 consistente, intraday e currency (sem Yahoo real)."""

import json

import pandas as pd
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import services.asset_service as svc_mod
from api import asset_router
from core.security import get_current_user
from infrastructure import providers as prov_mod
from infrastructure.providers import YahooFinanceProvider, format_ticker
from models.asset import AssetQuote, HistoryPoint
from services.asset_service import AssetService


class FakeCache:
    def __init__(self):
        self.store, self.ttls = {}, {}

    async def get(self, k):
        return self.store.get(k)

    async def set(self, k, v, ttl=None):
        self.store[k], self.ttls[k] = v, ttl


class FakeProvider:
    def __init__(self, missing=False):
        self.calls, self.missing = [], missing

    async def get_quote(self, t):
        self.calls.append(("quote", t))
        return AssetQuote(ticker=t, name="x", icon_url="", price_usd=1.0, direction="estável", currency="BRL")

    async def get_history(self, t, period, interval):
        self.calls.append(("history", t, period, interval))
        if self.missing:
            raise ValueError("nao encontrado")
        return [HistoryPoint(date="2024-01-01", close=1.0)]

    async def get_dividends(self, t):
        self.calls.append(("div", t))
        return []


@pytest.fixture(autouse=True)
def no_yf(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("sem rede")
    monkeypatch.setattr(svc_mod.yf, "Ticker", boom)


@pytest.mark.parametrize("raw,esperado", [
    ("petr4", "PETR4.SA"), ("PETR4.SA", "PETR4.SA"), ("btc", "BTC-USD"),
    ("BTC-USD", "BTC-USD"), ("aapl", "AAPL"),
])
def test_format_ticker(raw, esperado):
    assert format_ticker(raw) == esperado


async def test_ticker_normalizado_compartilha_cache():
    prov, cache = FakeProvider(), FakeCache()
    s = AssetService(prov, cache)
    await s.get_history("petr4", "1mo")
    await s.get_history("PETR4.SA", "1mo")
    assert [c[1] for c in prov.calls] == ["PETR4.SA"]  # segunda veio do cache
    assert "hist_PETR4.SA_1mo" in cache.store
    q = await s.get_asset_quote("PETR4")
    assert q.ticker == "PETR4.SA" and prov.calls[-1] == ("quote", "PETR4.SA")
    assert q.currency == "BRL"


async def test_history_1d_intraday_e_ttl_curto():
    prov, cache = FakeProvider(), FakeCache()
    s = AssetService(prov, cache)
    await s.get_history("AAPL", "1d")
    await s.get_history("AAPL", "1mo")
    assert prov.calls[0][3] == "5m" and prov.calls[1][3] == "1d"
    assert cache.ttls["hist_AAPL_1d"] <= 300 and cache.ttls["hist_AAPL_1mo"] == 3600


async def test_ticker_inexistente_404_sem_cache():
    cache = FakeCache()
    s = AssetService(FakeProvider(missing=True), cache)
    with pytest.raises(HTTPException) as e:
        await s.get_history("INVALIDXYZ", "1mo")
    assert e.value.status_code == 404 and not cache.store


async def test_dividendos_vazios_continuam_200():
    out = await AssetService(FakeProvider(), FakeCache()).get_dividends("AAPL")
    assert json.loads(out) == []


# ---- router ----
def test_period_invalido_422():
    app = FastAPI()
    app.include_router(asset_router.router)
    app.dependency_overrides[get_current_user] = lambda: object()
    app.dependency_overrides[asset_router.get_asset_service] = lambda: AssetService(FakeProvider(), FakeCache())
    c = TestClient(app)
    assert c.get("/assets/AAPL/history?period=bad").status_code == 422
    assert c.get("/assets/AAPL/history?period=1d").status_code == 200


# ---- provider (yfinance mockado) ----
class FakeStock:
    def __init__(self, info, hist=None, divs=None, news=None):
        self.info = info
        self._hist = hist if hist is not None else pd.DataFrame()
        self.dividends = divs if divs is not None else pd.Series(dtype=float)
        self.news = news or []

    def history(self, period, interval):
        return self._hist


def _provider(monkeypatch, stock):
    monkeypatch.setattr(prov_mod.yf, "Ticker", lambda t: stock)
    return YahooFinanceProvider()


async def test_provider_vazio_ticker_invalido_levanta(monkeypatch):
    p = _provider(monkeypatch, FakeStock({}))
    for call in (p.get_history("X", "1mo", "1d"), p.get_dividends("X"), p.get_news("X"), p.get_financials("X")):
        with pytest.raises(ValueError):
            await call


async def test_provider_vazio_ticker_valido_ok(monkeypatch):
    p = _provider(monkeypatch, FakeStock({"regularMarketPrice": 10, "currency": "BRL"}))
    assert await p.get_dividends("PETR4") == []
    assert await p.get_news("PETR4") == []
    assert (await p.get_quote("PETR4")).currency == "BRL"


async def test_provider_intraday_usa_datetime_iso(monkeypatch):
    idx = pd.DatetimeIndex(["2024-01-02 14:30"], tz="UTC")
    df = pd.DataFrame({"Close": [5.0]}, index=idx)
    p = _provider(monkeypatch, FakeStock({"regularMarketPrice": 1}, hist=df))
    assert (await p.get_history("AAPL", "1d", "5m"))[0].date.startswith("2024-01-02T14:30")
    assert (await p.get_history("AAPL", "1mo", "1d"))[0].date == "2024-01-02"
