"""Toda falha do stream tem que deixar rastro no log e no frame de erro.

Regressão do caso real: o app mostrou erro, o uvicorn registrou
`POST /ai/chat/stream 200 OK` e nada mais — os `yield error` não logavam nada.
"""

import json
import logging
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.logging_config import set_request_id
from infrastructure.ai.model_router import ModelProvider
from services.ai import chat_service as cs_mod
from services.ai.chat_service import AIChatService
from services.ai.context import UserContext

USER = UserContext(id=uuid4(), name="Felipe", investor_profile="MODERATE", watchlist=[])


class ErroDeCota(Exception):
    status_code = 429


class ErroDeChave(Exception):
    def __init__(self):
        super().__init__("API key not valid. Please pass a valid API key.")
        self.status_code = 401


class ErroMudo(Exception):
    """Exceção com str() vazio — comum em SDKs de LLM."""


class FakeDb:
    async def get_session(self, session_id, session_type=None, user_id=None, **kw):
        return None


class FakeRouter:
    def __init__(self, tem_groq=True):
        self.tem_groq = tem_groq

    def build(self, provider):
        return SimpleNamespace(id=f"modelo-{provider.value}")

    async def pick(self):
        return ModelProvider.GEMINI

    async def fallback_for(self, provider, exc):
        if not self.tem_groq or getattr(exc, "status_code", None) != 429:
            return None
        return ModelProvider.GROQ


class FakeRuntime:
    def __init__(self, router):
        self.db = FakeDb()
        self.model_router = router

    async def get_knowledge(self):
        return None


class FakeAgent:
    def __init__(self, model, falhar_em, eventos):
        self.model = model
        self._falhar_em = falhar_em
        self._eventos = eventos

    def arun(self, message, session_id=None, user_id=None, stream=False, **kw):
        return self._stream() if stream else self._run(session_id)

    async def _run(self, session_id):
        erro = self._falhar_em.get(self.model.id)
        if erro is not None:
            raise erro
        return SimpleNamespace(
            session_id=session_id,
            run_id="run-1",
            get_content_as_string=lambda: "ok",
            tools=[],
        )

    async def _stream(self):
        erro = self._falhar_em.get(self.model.id)
        if erro is not None:
            raise erro
        for evento in self._eventos:
            yield evento


def montar(monkeypatch, falhar_em=None, eventos=None, tem_groq=True):
    runtime = FakeRuntime(FakeRouter(tem_groq=tem_groq))
    monkeypatch.setattr(
        cs_mod,
        "build_agent",
        lambda **kw: FakeAgent(kw["model"], falhar_em or {}, eventos or []),
    )
    return AIChatService(runtime=runtime, asset_service=None)


def evento(nome, **campos):
    return SimpleNamespace(event=nome, **campos)


async def coletar(gerador):
    return [f async for f in gerador]


def parse(frame):
    linhas = frame.strip().split("\n")
    return linhas[0].removeprefix("event: "), json.loads(
        linhas[1].removeprefix("data: ")
    )


# --------------------------------------------------- frame de erro utilizável


async def test_frame_de_erro_carrega_o_request_id(monkeypatch):
    """É o que liga o print do usuário ao traceback no servidor."""
    set_request_id("req-do-teste")
    servico = montar(monkeypatch, falhar_em={"modelo-gemini": ErroDeChave()})

    nome, dados = parse((await coletar(servico.stream(USER, "oi")))[0])

    assert nome == "error"
    assert dados["request_id"] == "req-do-teste"


async def test_frame_de_erro_nunca_vem_com_detail_vazio(monkeypatch):
    """`str(exc)` vazio deixaria o app sem nada para mostrar."""
    servico = montar(monkeypatch, falhar_em={"modelo-gemini": ErroMudo()}, tem_groq=False)

    _, dados = parse((await coletar(servico.stream(USER, "oi")))[0])

    assert dados["detail"].strip()
    assert "ErroMudo" in dados["detail"]


async def test_run_error_sem_conteudo_ganha_mensagem_padrao(monkeypatch):
    eventos = [evento("RunError", content=None)]
    servico = montar(monkeypatch, eventos=eventos)

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]
    erro = next(d for n, d in frames if n == "error")

    assert erro["detail"].strip()


# ------------------------------------------------------------------ logging


async def test_falha_antes_do_primeiro_token_e_logada_com_traceback(
    monkeypatch, caplog
):
    caplog.set_level(logging.ERROR, logger="services.ai.chat_service")
    servico = montar(monkeypatch, falhar_em={"modelo-gemini": ErroDeChave()})

    await coletar(servico.stream(USER, "oi"))

    registros = [r for r in caplog.records if "antes do primeiro token" in r.getMessage()]
    assert registros, "a falha precisa aparecer no log"
    assert registros[0].exc_info is not None, "sem traceback não dá para investigar"


async def test_falha_durante_a_geracao_e_logada(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger="services.ai.chat_service")

    class AgentQueQuebraNoMeio(FakeAgent):
        async def _stream(self):
            yield evento("RunContent", content="parcial")
            raise ErroDeCota()

    monkeypatch.setattr(
        cs_mod,
        "build_agent",
        lambda **kw: AgentQueQuebraNoMeio(kw["model"], {}, []),
    )
    servico = AIChatService(runtime=FakeRuntime(FakeRouter()), asset_service=None)

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert frames[-1][0] == "error"
    registros = [r for r in caplog.records if "DURANTE a geração" in r.getMessage()]
    assert registros
    assert registros[0].exc_info is not None


async def test_run_error_do_agno_e_logado_como_error(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger="services.ai.chat_service")
    eventos = [
        evento("RunContent", content="parcial"),
        evento("RunError", content="modelo recusou a requisição"),
    ]
    servico = montar(monkeypatch, eventos=eventos)

    await coletar(servico.stream(USER, "oi"))

    assert any("abortou no meio" in r.getMessage() for r in caplog.records)


async def test_resposta_vazia_gera_aviso(monkeypatch, caplog):
    """Bolha em branco no app vira 'a IA deu erro'; precisa de rastro."""
    caplog.set_level(logging.WARNING, logger="services.ai.chat_service")
    servico = montar(monkeypatch, eventos=[])

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert frames[-1][0] == "done"
    assert any("nenhum token gerado" in r.getMessage() for r in caplog.records)


async def test_conclusao_normal_loga_duracao_e_tools(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="services.ai.chat_service")
    eventos = [
        evento("ToolCallStarted", tool=SimpleNamespace(tool_name="cotacao_atual")),
        evento("RunContent", content="PETR4 a R$ 38,42"),
    ]
    servico = montar(monkeypatch, eventos=eventos)

    await coletar(servico.stream(USER, "oi"))

    concluido = [r for r in caplog.records if "stream concluído" in r.getMessage()]
    assert concluido
    assert "cotacao_atual" in concluido[0].getMessage()


async def test_tool_call_error_do_agno_e_logado(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger="services.ai.chat_service")
    eventos = [
        evento(
            "ToolCallError",
            tool=SimpleNamespace(tool_name="cotacao_atual", tool_call_error="timeout"),
            content=None,
        ),
        evento("RunContent", content="segue"),
    ]
    servico = montar(monkeypatch, eventos=eventos)

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    # O erro de tool não vira frame para o app — o agente ainda pode se virar.
    assert [n for n, _ in frames] == ["start", "token", "done"]
    assert any("tool cotacao_atual FALHOU" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    "erro,esperado_no_log",
    [
        (ErroDeCota(), "caindo para a Groq"),
        (ErroDeChave(), "NÃO transitório"),
    ],
)
async def test_router_explica_a_decisao_de_fallback(erro, esperado_no_log, caplog):
    """Sem isso, 'não trocou de modelo' vira adivinhação."""
    from infrastructure.ai.model_router import ModelRouter

    caplog.set_level(logging.WARNING, logger="infrastructure.ai.model_router")

    class CacheFake:
        async def get(self, key):
            return None

        async def set(self, key, value, ttl=60):
            return None

    router = ModelRouter(
        CacheFake(), google_api_key="g", groq_api_key="q"
    )
    await router.fallback_for(ModelProvider.GEMINI, erro)

    assert any(esperado_no_log in r.getMessage() for r in caplog.records)
