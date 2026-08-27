"""Endpoints /ai: contrato HTTP e tradução de erros do serviço."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import main
from api import ai_router
from core.security import get_current_user
from services.ai.chat_service import AgentUnavailable, ChatResult, SessionNotFound
from services.ai.context import UserContext

USER_ID = uuid4()


class FakeChatService:
    """Registra o que foi pedido e devolve o que o teste mandar devolver."""

    def __init__(self, erro=None):
        self.erro = erro
        self.chamadas = []

    def _talvez_falhar(self):
        if self.erro is not None:
            raise self.erro

    async def assert_can_use_session(self, session_id, user_id):
        self.chamadas.append(("assert", session_id, user_id))
        self._talvez_falhar()

    async def chat(self, user_ctx, message, session_id=None):
        self.chamadas.append(("chat", session_id, message))
        self._talvez_falhar()
        return ChatResult(
            session_id=session_id or "nova-sessao",
            run_id="run-1",
            content="O ROE mede o retorno sobre o patrimônio líquido.",
            model_used="gemini-3.5-flash",
            provider="gemini",
            tools_used=["cotacao_atual"],
        )

    async def stream(self, user_ctx, message, session_id=None):
        self.chamadas.append(("stream", session_id, message))
        yield 'event: start\ndata: {"session_id": "s1"}\n\n'
        yield 'event: token\ndata: {"content": "oi"}\n\n'
        yield 'event: done\ndata: {"content": "oi"}\n\n'

    async def list_sessions(self, user_id, limit=50):
        self.chamadas.append(("list", user_id, limit))
        self._talvez_falhar()
        return [
            {
                "session_id": "s1",
                "created_at": 1,
                "updated_at": 2,
                "runs_count": 3,
                "summary": "Conversa sobre dividendos",
                "topics": ["DY", "payout"],
            }
        ]

    async def get_session_messages(self, session_id, user_id):
        self.chamadas.append(("mensagens", session_id, user_id))
        self._talvez_falhar()
        return [{"role": "user", "content": "o que é ROE?", "created_at": 1}]

    async def get_session_summary(self, session_id, user_id):
        self.chamadas.append(("resumo", session_id, user_id))
        self._talvez_falhar()
        return {
            "session_id": session_id,
            "summary": "Falamos de ROE",
            "topics": ["ROE"],
            "updated_at": None,
        }

    async def delete_session(self, session_id, user_id):
        self.chamadas.append(("delete", session_id, user_id))
        self._talvez_falhar()


@pytest.fixture
def cliente():
    """TestClient com auth, contexto do usuário e serviço substituídos."""
    servico = FakeChatService()

    main.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=USER_ID, name="Felipe", investor_profile="MODERATE"
    )
    main.app.dependency_overrides[ai_router.get_user_context] = lambda: UserContext(
        id=USER_ID, name="Felipe", investor_profile="MODERATE", watchlist=[]
    )
    main.app.dependency_overrides[ai_router.get_chat_service] = lambda: servico

    with TestClient(main.app) as client:
        yield client, servico

    main.app.dependency_overrides.clear()


# --------------------------------------------------------------------- sucesso


def test_chat_devolve_resposta_e_metadados(cliente):
    client, _ = cliente

    r = client.post("/ai/chat", json={"message": "o que é ROE?"})

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["session_id"] == "nova-sessao"
    assert corpo["provider"] == "gemini"
    assert corpo["model_used"] == "gemini-3.5-flash"
    assert corpo["tools_used"] == ["cotacao_atual"]
    assert "ROE" in corpo["content"]


def test_chat_sem_mensagem_e_rejeitado(cliente):
    client, _ = cliente
    assert client.post("/ai/chat", json={"message": ""}).status_code == 422


def test_stream_devolve_sse(cliente):
    client, _ = cliente

    r = client.post("/ai/chat/stream", json={"message": "oi"})

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: start" in r.text
    assert "event: done" in r.text


def test_listar_sessoes(cliente):
    client, _ = cliente

    r = client.get("/ai/sessions")

    assert r.status_code == 200
    assert r.json()[0]["session_id"] == "s1"
    assert r.json()[0]["topics"] == ["DY", "payout"]


def test_historico_da_sessao(cliente):
    client, _ = cliente

    r = client.get("/ai/sessions/s1")

    assert r.status_code == 200
    assert r.json()["messages"][0]["content"] == "o que é ROE?"


def test_resumo_da_sessao(cliente):
    client, _ = cliente

    r = client.get("/ai/sessions/s1/summary")

    assert r.status_code == 200
    assert r.json()["summary"] == "Falamos de ROE"


def test_deletar_sessao(cliente):
    client, servico = cliente

    r = client.delete("/ai/sessions/s1")

    assert r.status_code == 204
    assert ("delete", "s1", str(USER_ID)) in servico.chamadas


# ------------------------------------------------- sessão de outro usuário


@pytest.mark.parametrize(
    "metodo,url,payload",
    [
        ("post", "/ai/chat", {"message": "oi", "session_id": "alheia"}),
        ("post", "/ai/chat/stream", {"message": "oi", "session_id": "alheia"}),
        ("get", "/ai/sessions/alheia", None),
        ("get", "/ai/sessions/alheia/summary", None),
        ("delete", "/ai/sessions/alheia", None),
    ],
)
def test_sessao_de_outro_usuario_devolve_404(metodo, url, payload):
    """404 e não 403: distinguir os dois já confirmaria que o id existe."""
    servico = FakeChatService(erro=SessionNotFound("alheia"))

    main.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=USER_ID, name="Felipe", investor_profile="MODERATE"
    )
    main.app.dependency_overrides[ai_router.get_user_context] = lambda: UserContext(
        id=USER_ID, name="Felipe", investor_profile="MODERATE", watchlist=[]
    )
    main.app.dependency_overrides[ai_router.get_chat_service] = lambda: servico

    try:
        with TestClient(main.app) as client:
            r = getattr(client, metodo)(url, **({"json": payload} if payload else {}))
        assert r.status_code == 404
    finally:
        main.app.dependency_overrides.clear()


def test_stream_valida_posse_antes_de_abrir_o_stream():
    """Depois que o 200 do stream começou, não dá mais para virar 404."""
    servico = FakeChatService(erro=SessionNotFound("alheia"))

    main.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=USER_ID, name="Felipe", investor_profile="MODERATE"
    )
    main.app.dependency_overrides[ai_router.get_user_context] = lambda: UserContext(
        id=USER_ID, name="Felipe", investor_profile="MODERATE", watchlist=[]
    )
    main.app.dependency_overrides[ai_router.get_chat_service] = lambda: servico

    try:
        with TestClient(main.app) as client:
            r = client.post(
                "/ai/chat/stream", json={"message": "oi", "session_id": "alheia"}
            )
        assert r.status_code == 404
        assert servico.chamadas[0][0] == "assert"
        assert not any(c[0] == "stream" for c in servico.chamadas)
    finally:
        main.app.dependency_overrides.clear()


# ----------------------------------------------------------- provider fora


def test_agente_indisponivel_vira_502():
    servico = FakeChatService(erro=AgentUnavailable("429 quota exceeded"))

    main.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=USER_ID, name="Felipe", investor_profile="MODERATE"
    )
    main.app.dependency_overrides[ai_router.get_user_context] = lambda: UserContext(
        id=USER_ID, name="Felipe", investor_profile="MODERATE", watchlist=[]
    )
    main.app.dependency_overrides[ai_router.get_chat_service] = lambda: servico

    try:
        with TestClient(main.app) as client:
            r = client.post("/ai/chat", json={"message": "oi"})
        assert r.status_code == 502
        assert "quota" in r.json()["detail"]
    finally:
        main.app.dependency_overrides.clear()


# ------------------------------------------------------------------- auth


def test_endpoints_de_ia_exigem_autenticacao():
    main.app.dependency_overrides.clear()
    with TestClient(main.app) as client:
        assert client.post("/ai/chat", json={"message": "oi"}).status_code == 401
        assert client.get("/ai/sessions").status_code == 401
