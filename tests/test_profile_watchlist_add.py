"""POST /profile/watchlist/add: ticker inexistente -> 422, lista vazia -> 422,
provider fora do ar -> aceita (fail open)."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api import profile_router
from api.asset_router import get_asset_service
from core.security import get_current_user
from infrastructure.database import get_db


class FakeQuery:
    def __init__(self, wl): self.wl = wl
    def filter(self, *_): return self
    def with_for_update(self): return self
    def first(self): return self.wl


class FakeDb:
    def __init__(self, wl=None): self.wl, self.added, self.commits = wl, [], 0
    def query(self, _): return FakeQuery(self.wl)
    def add(self, o): self.added.append(o)
    def commit(self): self.commits += 1


class FakeService:
    def __init__(self, behavior): self.behavior, self.calls = behavior, []
    async def get_asset_quote(self, ticker):
        self.calls.append(ticker)
        r = self.behavior(ticker)
        if isinstance(r, BaseException):
            raise r
        return r


def client(service, db):
    app = FastAPI()
    app.include_router(profile_router.router)
    app.dependency_overrides[get_asset_service] = lambda: service
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": 1})()
    return TestClient(app)


A = lambda t: {"ticker": t, "name": t, "icon_url": ""}
NOT_FOUND = HTTPException(404, "nao encontrado")


def test_empty_list_is_422():
    db = FakeDb()
    r = client(FakeService(lambda t: "ok"), db).post("/profile/watchlist/add", json=[])
    assert r.status_code == 422 and db.commits == 0


def test_unknown_ticker_rejected_nothing_saved():
    db = FakeDb()
    s = FakeService(lambda t: NOT_FOUND if t == "ZZZZ99X" else "ok")
    r = client(s, db).post("/profile/watchlist/add", json=[A("PETR4"), A("ZZZZ99X")])
    assert r.status_code == 422 and "ZZZZ99X" in r.json()["detail"]
    assert db.commits == 0 and not db.added
    assert sorted(s.calls) == ["PETR4", "ZZZZ99X"]  # ticker como digitado


def test_provider_down_fails_open():
    db = FakeDb()
    s = FakeService(lambda t: TimeoutError())
    r = client(s, db).post("/profile/watchlist/add", json=[A("PETR4")])
    assert r.status_code == 200 and db.commits == 1
    assert db.added[0].tickers == [A("PETR4")]


def test_5xx_from_service_fails_open():
    r = client(FakeService(lambda t: HTTPException(502, "x")), FakeDb()).post(
        "/profile/watchlist/add", json=[A("AAPL")])
    assert r.status_code == 200


def test_all_duplicates_still_400():
    wl = type("W", (), {"tickers": [A("AAPL")]})()
    r = client(FakeService(lambda t: "ok"), FakeDb(wl)).post("/profile/watchlist/add", json=[A("AAPL")])
    assert r.status_code == 400
    assert r.json()["detail"] == "Todos os ativos já estão na sua lista."
