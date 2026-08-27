"""Isolamento de sessões entre usuários.

Sem estas regras, mandar um `session_id` alheio em `POST /ai/chat` carregaria o
histórico do dono dele para dentro do contexto do modelo.
"""

from types import SimpleNamespace

import pytest

from services.ai.chat_service import AIChatService, SessionNotFound

MEU_ID = "11111111-1111-1111-1111-111111111111"
OUTRO_ID = "22222222-2222-2222-2222-222222222222"


class FakeDb:
    """Reproduz o comportamento do AsyncPostgresDb que importa aqui.

    Detalhe central: `get_session` com `user_id` filtra — sessão de outro
    usuário volta como None, indistinguível de "não existe".
    """

    def __init__(self, sessoes=None):
        self.sessoes = dict(sessoes or {})
        self.deletadas = []
        self.chamadas_get = []

    async def get_session(self, session_id, session_type=None, user_id=None, **kwargs):
        self.chamadas_get.append({"session_id": session_id, "user_id": user_id})
        sessao = self.sessoes.get(session_id)
        if sessao is None:
            return None
        if user_id is not None and sessao.user_id != user_id:
            return None
        return sessao

    async def get_sessions(self, **kwargs):
        return [s for s in self.sessoes.values() if s.user_id == kwargs.get("user_id")]

    async def delete_session(self, session_id, user_id=None):
        self.deletadas.append((session_id, user_id))
        return True


def sessao(session_id, user_id, **extras):
    return SimpleNamespace(session_id=session_id, user_id=user_id, **extras)


def servico(db):
    runtime = SimpleNamespace(db=db)
    return AIChatService(runtime=runtime, asset_service=None)


# ----------------------------------------------------- retomar uma conversa


async def test_pode_retomar_a_propria_sessao():
    db = FakeDb({"s1": sessao("s1", MEU_ID)})
    await servico(db).assert_can_use_session("s1", MEU_ID)


async def test_id_desconhecido_e_tratado_como_sessao_nova():
    db = FakeDb()
    await servico(db).assert_can_use_session("ainda-nao-existe", MEU_ID)


async def test_nao_pode_retomar_sessao_de_outro_usuario():
    db = FakeDb({"s1": sessao("s1", OUTRO_ID)})
    with pytest.raises(SessionNotFound):
        await servico(db).assert_can_use_session("s1", MEU_ID)


async def test_checagem_de_posse_busca_sem_filtro_de_user_id():
    """Com o filtro, sessão de terceiro voltaria None e seria sobrescrita."""
    db = FakeDb({"s1": sessao("s1", OUTRO_ID)})
    with pytest.raises(SessionNotFound):
        await servico(db).assert_can_use_session("s1", MEU_ID)

    assert db.chamadas_get[0]["user_id"] is None


# ------------------------------------------------------------------- leitura


async def test_ler_mensagens_de_sessao_alheia_falha():
    db = FakeDb({"s1": sessao("s1", OUTRO_ID, get_chat_history=lambda: [])})
    with pytest.raises(SessionNotFound):
        await servico(db).get_session_messages("s1", MEU_ID)


async def test_ler_mensagens_da_propria_sessao():
    mensagens = [SimpleNamespace(role="user", content="oi", created_at=1)]
    db = FakeDb({"s1": sessao("s1", MEU_ID, get_chat_history=lambda: mensagens)})

    resultado = await servico(db).get_session_messages("s1", MEU_ID)

    assert resultado == [{"role": "user", "content": "oi", "created_at": 1}]


async def test_resumo_de_sessao_alheia_falha():
    db = FakeDb({"s1": sessao("s1", OUTRO_ID, get_session_summary=lambda: None)})
    with pytest.raises(SessionNotFound):
        await servico(db).get_session_summary("s1", MEU_ID)


async def test_listagem_so_traz_sessoes_do_usuario():
    db = FakeDb(
        {
            "s1": sessao("s1", MEU_ID, summary=None, runs=[], created_at=1, updated_at=2),
            "s2": sessao("s2", OUTRO_ID, summary=None, runs=[], created_at=1, updated_at=2),
        }
    )

    resultado = await servico(db).list_sessions(MEU_ID)

    assert [s["session_id"] for s in resultado] == ["s1"]


# ------------------------------------------------------------------ exclusão


async def test_nao_deleta_sessao_de_outro_usuario():
    db = FakeDb({"s1": sessao("s1", OUTRO_ID)})

    with pytest.raises(SessionNotFound):
        await servico(db).delete_session("s1", MEU_ID)

    assert db.deletadas == [], "não pode chegar a chamar o delete"


async def test_deleta_a_propria_sessao():
    db = FakeDb({"s1": sessao("s1", MEU_ID)})

    await servico(db).delete_session("s1", MEU_ID)

    assert db.deletadas == [("s1", MEU_ID)]


async def test_deletar_sessao_inexistente_falha():
    db = FakeDb()
    with pytest.raises(SessionNotFound):
        await servico(db).delete_session("nao-existe", MEU_ID)
