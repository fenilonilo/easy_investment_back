"""Fallback e streaming no AIChatService.

Aqui o roteador de modelos encontra o fluxo real: uma run que falha por cota
tem que ser repetida na Groq, e o cliente não pode perceber a troca.
"""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from agno.run.base import RunStatus

from infrastructure.ai.model_router import ModelProvider, is_availability_error
from services.ai import chat_service as cs_mod
from services.ai.chat_service import AgentUnavailable, AIChatService
from services.ai.context import UserContext

USER = UserContext(
    id=uuid4(), name="Felipe", investor_profile="MODERATE", watchlist=[]
)


class ErroDeCota(Exception):
    status_code = 429


class ErroDeChave(Exception):
    def __init__(self):
        super().__init__("API key not valid. Please pass a valid API key.")
        self.status_code = 401


class FakeDb:
    async def get_session(self, session_id, session_type=None, user_id=None, **kw):
        return None


class FakeRouter:
    """Router de verdade em miniatura: mesma semântica, sem Redis nem SDK."""

    def __init__(self, provider_inicial=ModelProvider.GEMINI, tem_groq=True):
        self.provider_inicial = provider_inicial
        self.tem_groq = tem_groq
        self.quarentenas = 0

    def build(self, provider):
        return SimpleNamespace(id=f"modelo-{provider.value}")

    async def pick(self):
        return self.provider_inicial

    async def fallback_for(self, provider, exc):
        if provider is not ModelProvider.GEMINI or not self.tem_groq:
            return None
        if not is_availability_error(exc):
            return None
        self.quarentenas += 1
        return ModelProvider.GROQ


class FakeRuntime:
    def __init__(self, router):
        self.db = FakeDb()
        self.model_router = router

    async def get_knowledge(self):
        return None


class FakeAgent:
    """Falha nos modelos listados em `falhar_em`, responde nos demais."""

    def __init__(self, model, falhar_em, eventos=None):
        self.model = model
        self._falhar_em = falhar_em
        self._eventos = eventos or []
        self._tools_erro = []
        # eventos por modelo, para simular `run_error` só no Gemini
        if isinstance(self._eventos, dict):
            self._eventos = self._eventos.get(model.id, [])

    def arun(self, message, session_id=None, user_id=None, stream=False, **kw):
        """Espelha o contrato do agno: `def`, não `async def`.

        Devolve uma coroutine quando `stream=False` e um async generator
        quando `stream=True`. Um fake `async def` devolveria coroutine nos
        dois casos e esconderia o `await` indevido no caminho de streaming.
        """
        if stream:
            return self._stream()
        return self._run(session_id)

    async def _run(self, session_id):
        erro = self._falhar_em.get(self.model.id)
        if isinstance(erro, str):
            # Como o agno: sem levantar, devolve RunOutput com status ERROR.
            return SimpleNamespace(
                session_id=session_id,
                run_id="run-1",
                status=RunStatus.error,
                content=erro,
                get_content_as_string=lambda: erro,
                tools=self._tools_erro,
            )
        if erro is not None:
            raise erro
        return SimpleNamespace(
            session_id=session_id,
            run_id="run-1",
            get_content_as_string=lambda: f"resposta de {self.model.id}",
            tools=[SimpleNamespace(tool_name="cotacao_atual")],
        )

    async def _stream(self):
        # Como no agno, a falha só aparece na primeira iteração — o generator
        # em si é criado sem erro.
        erro = self._falhar_em.get(self.model.id)
        if erro is not None:
            raise erro
        for evento in self._eventos:
            yield evento


def montar(monkeypatch, falhar_em=None, eventos=None, router=None, tools_erro=None):
    router = router or FakeRouter()
    runtime = FakeRuntime(router)

    def fabrica(**kw):
        agente = FakeAgent(kw["model"], falhar_em or {}, eventos)
        agente._tools_erro = tools_erro or []
        return agente

    monkeypatch.setattr(cs_mod, "build_agent", fabrica)
    return AIChatService(runtime=runtime, asset_service=None), router


# ------------------------------------------------------------------- chat()


async def test_responde_pelo_gemini_quando_ele_esta_ok(monkeypatch):
    servico, _ = montar(monkeypatch)

    resultado = await servico.chat(USER, "oi")

    assert resultado.provider == "gemini"
    assert resultado.content == "resposta de modelo-gemini"
    assert resultado.tools_used == ["cotacao_atual"]


async def test_cai_para_groq_quando_gemini_estoura_cota(monkeypatch):
    servico, router = montar(monkeypatch, falhar_em={"modelo-gemini": ErroDeCota()})

    resultado = await servico.chat(USER, "oi")

    assert resultado.provider == "groq"
    assert resultado.content == "resposta de modelo-groq"
    assert router.quarentenas == 1


async def test_erro_de_chave_nao_dispara_fallback(monkeypatch):
    servico, router = montar(monkeypatch, falhar_em={"modelo-gemini": ErroDeChave()})

    with pytest.raises(AgentUnavailable) as info:
        await servico.chat(USER, "oi")

    assert "API key" not in str(info.value)  # texto cru só no log/.raw
    assert "API key not valid" in info.value.raw

    assert router.quarentenas == 0


async def test_falha_nos_dois_providers_vira_agent_unavailable(monkeypatch):
    servico, _ = montar(
        monkeypatch,
        falhar_em={"modelo-gemini": ErroDeCota(), "modelo-groq": ErroDeCota()},
    )

    with pytest.raises(AgentUnavailable):
        await servico.chat(USER, "oi")


async def test_gera_session_id_quando_nao_recebe_um(monkeypatch):
    servico, _ = montar(monkeypatch)

    resultado = await servico.chat(USER, "oi")

    assert resultado.session_id
    assert resultado.session_id != ""


# ------------------------------------------------------------------ stream()


def evento(nome, **campos):
    return SimpleNamespace(event=nome, **campos)


async def coletar(gerador):
    frames = []
    async for frame in gerador:
        frames.append(frame)
    return frames


def parse(frame):
    linhas = frame.strip().split("\n")
    nome = linhas[0].removeprefix("event: ")
    dados = json.loads(linhas[1].removeprefix("data: "))
    return nome, dados


async def test_stream_traduz_eventos_do_agno_em_sse(monkeypatch):
    eventos = [
        evento("RunContent", content="O ROE "),
        evento("ToolCallStarted", tool=SimpleNamespace(tool_name="cotacao_atual")),
        evento("RunContent", content="mede o retorno."),
        evento("RunCompleted", content="ignorado"),
    ]
    servico, _ = montar(monkeypatch, eventos=eventos)

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]
    nomes = [n for n, _ in frames]

    assert nomes == ["start", "token", "tool", "token", "done"]
    assert frames[2][1]["name"] == "cotacao_atual"
    assert frames[-1][1]["content"] == "O ROE mede o retorno."


async def test_stream_cai_para_groq_antes_do_primeiro_token(monkeypatch):
    eventos = [evento("RunContent", content="oi")]
    servico, router = montar(
        monkeypatch, falhar_em={"modelo-gemini": ErroDeCota()}, eventos=eventos
    )

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert frames[0][0] == "start"
    assert frames[0][1]["provider"] == "groq"
    assert router.quarentenas == 1
    assert "error" not in [n for n, _ in frames]


async def test_stream_emite_error_quando_nao_ha_fallback(monkeypatch):
    servico, _ = montar(monkeypatch, falhar_em={"modelo-gemini": ErroDeChave()})

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert len(frames) == 1
    assert frames[0][0] == "error"
    assert "API key" not in frames[0][1]["detail"]
    assert frames[0][1]["detail"] == cs_mod.MSG_GENERICA


async def test_stream_repassa_run_error_do_agno(monkeypatch):
    eventos = [
        evento("RunContent", content="parcial"),
        evento("RunError", content="modelo recusou a requisição"),
    ]
    servico, _ = montar(monkeypatch, eventos=eventos)

    nomes = [parse(f)[0] for f in await coletar(servico.stream(USER, "oi"))]

    # Sem `done` depois do erro: o app o leria como resposta vazia bem-sucedida.
    assert nomes == ["start", "token", "error"]


# ----------------------------------------- run_error / status ERROR (agno real)

GEMINI_503 = (
    '{ "error": { "code": 503, "message": "The model is overloaded.", '
    '"status": "UNAVAILABLE" } }'
)
GEMINI_429 = "429 RESOURCE_EXHAUSTED. quota exceeded"


async def test_stream_run_error_antes_do_token_cai_para_groq(monkeypatch):
    """Regressão: com stream_events=True o 503 vem como evento, não exceção."""
    eventos = {
        "modelo-gemini": [
            evento("RunStarted"),
            evento("RunError", content=GEMINI_503),
        ],
        "modelo-groq": [
            evento("RunStarted"),
            evento("RunContent", content="resposta da groq"),
        ],
    }
    servico, router = montar(monkeypatch, eventos=eventos)

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert [n for n, _ in frames] == ["start", "token", "done"]  # um só start
    assert frames[0][1]["provider"] == "groq"
    assert frames[-1][1]["content"] == "resposta da groq"
    assert router.quarentenas == 1


async def test_stream_run_error_de_chave_nao_cai_para_groq(monkeypatch):
    eventos = {"modelo-gemini": [evento("RunError", content="API key not valid.")]}
    servico, router = montar(monkeypatch, eventos=eventos)

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert [n for n, _ in frames] == ["error"]
    assert router.quarentenas == 0


async def test_stream_detail_nao_vaza_json_do_provider(monkeypatch):
    eventos = [evento("RunError", content=GEMINI_503)]
    servico, _ = montar(monkeypatch, eventos=eventos, router=FakeRouter(tem_groq=False))

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert frames[0][1]["detail"] == cs_mod.MSG_INDISPONIVEL


async def test_stream_detail_de_cota_tem_variante_propria(monkeypatch):
    eventos = [evento("RunError", content=GEMINI_429)]
    servico, _ = montar(monkeypatch, eventos=eventos, router=FakeRouter(tem_groq=False))

    frames = [parse(f) for f in await coletar(servico.stream(USER, "oi"))]

    assert frames[0][1]["detail"] == cs_mod.MSG_COTA


async def test_stream_nao_repete_depois_de_write_tool(monkeypatch):
    eventos = {
        "modelo-gemini": [
            evento("ToolCallStarted", tool=SimpleNamespace(tool_name="adicionar_a_watchlist")),
            evento("RunError", content=GEMINI_503),
        ],
    }
    servico, router = montar(monkeypatch, eventos=eventos)

    nomes = [parse(f)[0] for f in await coletar(servico.stream(USER, "oi"))]

    assert nomes == ["start", "tool", "error"]
    assert router.quarentenas == 0


async def test_stream_com_groq_tambem_falhando_emite_so_error(monkeypatch):
    eventos = [evento("RunStarted"), evento("RunError", content=GEMINI_503)]
    servico, _ = montar(monkeypatch, eventos=eventos)

    nomes = [parse(f)[0] for f in await coletar(servico.stream(USER, "oi"))]

    assert nomes == ["error"]


async def test_chat_status_error_cai_para_groq(monkeypatch):
    servico, router = montar(monkeypatch, falhar_em={"modelo-gemini": GEMINI_503})

    resultado = await servico.chat(USER, "oi")

    assert resultado.provider == "groq"
    assert resultado.content == "resposta de modelo-groq"
    assert router.quarentenas == 1


async def test_chat_status_error_sem_fallback_levanta_agent_unavailable(monkeypatch):
    servico, _ = montar(
        monkeypatch,
        falhar_em={"modelo-gemini": GEMINI_503, "modelo-groq": GEMINI_503},
    )

    with pytest.raises(AgentUnavailable) as info:
        await servico.chat(USER, "oi")

    assert str(info.value) == cs_mod.MSG_INDISPONIVEL
    assert "overloaded" in info.value.raw


async def test_chat_status_error_apos_write_tool_nao_repete(monkeypatch):
    servico, router = montar(
        monkeypatch,
        falhar_em={"modelo-gemini": GEMINI_503},
        tools_erro=[SimpleNamespace(tool_name="remover_da_watchlist")],
    )

    with pytest.raises(AgentUnavailable):
        await servico.chat(USER, "oi")

    assert router.quarentenas == 0


# ---------------------------------------------------- histórico sem contexto


async def test_historico_remove_o_contexto_injetado(monkeypatch):
    msg = SimpleNamespace(
        role="user",
        content='oi\n\n<additional context>\n{"nome": "Felipe"}\n</additional context>',
        created_at=1,
    )
    sessao = SimpleNamespace(get_chat_history=lambda: [msg])
    servico, _ = montar(monkeypatch)

    async def get_session(**kw):
        return sessao

    servico.runtime.db.get_session = get_session

    mensagens = await servico.get_session_messages("s1", "u1")

    assert mensagens[0]["content"] == "oi"
