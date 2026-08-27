"""Tools de escrita na watchlist.

Dois pontos que precisam de rede de segurança:
1. o `user_id` vem do JWT e fica no closure — o modelo não consegue trocá-lo;
2. mutação em coluna JSONB exige `flag_modified`, senão o commit não persiste.
"""

from uuid import uuid4

import pytest

from services.ai import tools as tools_mod


class FakeWatchlist:
    def __init__(self, user_id, tickers):
        self.user_id = user_id
        self.tickers = tickers


class FakeQuery:
    def __init__(self, resultado):
        self._resultado = resultado
        self.filtros = []

    def filter(self, criterio):
        self.filtros.append(criterio)
        return self

    def first(self):
        return self._resultado


class FakeSession:
    def __init__(self, watchlist=None):
        self.watchlist = watchlist
        self.commits = 0
        self.adicionados = []
        self.fechada = False
        self.ultima_query = None

    def query(self, modelo):
        self.ultima_query = FakeQuery(self.watchlist)
        return self.ultima_query

    def add(self, obj):
        self.adicionados.append(obj)

    def commit(self):
        self.commits += 1

    def close(self):
        self.fechada = True


@pytest.fixture
def ambiente(monkeypatch):
    """Substitui SessionLocal e espiona flag_modified."""
    estado = {"session": None, "flags": []}

    def instalar(watchlist=None):
        sessao = FakeSession(watchlist)
        estado["session"] = sessao
        monkeypatch.setattr(tools_mod, "SessionLocal", lambda: sessao)
        return sessao

    monkeypatch.setattr(
        tools_mod,
        "flag_modified",
        lambda obj, campo: estado["flags"].append((obj, campo)),
    )
    estado["instalar"] = instalar
    return estado


# ------------------------------------------------------------------- adicionar


async def test_adiciona_ticker_novo(ambiente):
    user_id = uuid4()
    sessao = ambiente["instalar"](FakeWatchlist(user_id, [{"ticker": "AAPL"}]))
    adicionar, _ = tools_mod.build_watchlist_tools(user_id)

    resposta = await adicionar("petr4", "Petrobras PN")

    assert "PETR4" in resposta
    assert [i["ticker"] for i in sessao.watchlist.tickers] == ["AAPL", "PETR4"]
    assert sessao.commits == 1
    assert sessao.fechada is True


async def test_adicionar_chama_flag_modified(ambiente):
    """Sem isto o SQLAlchemy não detecta a mudança no JSONB e o commit é no-op."""
    user_id = uuid4()
    sessao = ambiente["instalar"](FakeWatchlist(user_id, [{"ticker": "AAPL"}]))
    adicionar, _ = tools_mod.build_watchlist_tools(user_id)

    await adicionar("PETR4")

    assert ambiente["flags"] == [(sessao.watchlist, "tickers")]


async def test_adicionar_ticker_repetido_nao_duplica(ambiente):
    user_id = uuid4()
    sessao = ambiente["instalar"](FakeWatchlist(user_id, [{"ticker": "PETR4"}]))
    adicionar, _ = tools_mod.build_watchlist_tools(user_id)

    resposta = await adicionar("PETR4")

    assert "já estava" in resposta
    assert len(sessao.watchlist.tickers) == 1
    assert sessao.commits == 0


async def test_cria_watchlist_quando_usuario_ainda_nao_tem(ambiente):
    user_id = uuid4()
    sessao = ambiente["instalar"](None)
    adicionar, _ = tools_mod.build_watchlist_tools(user_id)

    await adicionar("BTC")

    assert len(sessao.adicionados) == 1
    assert sessao.adicionados[0].user_id == user_id
    assert sessao.commits == 1


async def test_ticker_vazio_e_rejeitado_sem_tocar_no_banco(ambiente):
    user_id = uuid4()
    sessao = ambiente["instalar"](FakeWatchlist(user_id, []))
    adicionar, _ = tools_mod.build_watchlist_tools(user_id)

    resposta = await adicionar("   ")

    assert resposta == "Ticker inválido."
    assert sessao.commits == 0


# ---------------------------------------------------------------------- remover


async def test_remove_ticker_existente(ambiente):
    user_id = uuid4()
    sessao = ambiente["instalar"](
        FakeWatchlist(user_id, [{"ticker": "PETR4"}, {"ticker": "AAPL"}])
    )
    _, remover = tools_mod.build_watchlist_tools(user_id)

    resposta = await remover("petr4")

    assert "removido" in resposta
    assert [i["ticker"] for i in sessao.watchlist.tickers] == ["AAPL"]
    assert ambiente["flags"] == [(sessao.watchlist, "tickers")]
    assert sessao.commits == 1


async def test_remover_ticker_ausente_nao_commita(ambiente):
    user_id = uuid4()
    sessao = ambiente["instalar"](FakeWatchlist(user_id, [{"ticker": "AAPL"}]))
    _, remover = tools_mod.build_watchlist_tools(user_id)

    resposta = await remover("PETR4")

    assert "não está" in resposta
    assert sessao.commits == 0


async def test_remover_de_watchlist_vazia(ambiente):
    user_id = uuid4()
    ambiente["instalar"](FakeWatchlist(uuid4(), []))
    _, remover = tools_mod.build_watchlist_tools(user_id)

    assert "vazia" in await remover("PETR4")


# ------------------------------------------------------------------- isolamento


async def test_tool_nao_aceita_user_id_do_modelo():
    """A assinatura exposta ao LLM não pode ter como alcançar outro usuário."""
    import inspect

    adicionar, remover = tools_mod.build_watchlist_tools(uuid4())

    for tool in (adicionar, remover):
        params = set(inspect.signature(tool).parameters)
        assert not params & {"user_id", "usuario", "user", "id"}, (
            f"{tool.__name__} expõe identidade do usuário ao modelo"
        )


async def test_cada_tool_fica_presa_ao_seu_proprio_usuario(monkeypatch):
    """Duas instâncias das tools não podem enxergar a lista uma da outra."""
    usuario_a, usuario_b = uuid4(), uuid4()
    consultados = []

    class SessaoEspia(FakeSession):
        def query(self, modelo):
            consultados.append(self)
            return FakeQuery(None)

    monkeypatch.setattr(tools_mod, "SessionLocal", lambda: SessaoEspia())

    adicionar_a, _ = tools_mod.build_watchlist_tools(usuario_a)
    adicionar_b, _ = tools_mod.build_watchlist_tools(usuario_b)

    await adicionar_a("PETR4")
    await adicionar_b("VALE3")

    assert consultados[0].adicionados[0].user_id == usuario_a
    assert consultados[1].adicionados[0].user_id == usuario_b
