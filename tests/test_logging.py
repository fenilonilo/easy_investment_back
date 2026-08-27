"""Observabilidade: correlação por request e descrição de exceções.

O que está aqui existe para um cenário concreto: o usuário reporta "a IA deu
erro" e a gente precisa achar o traceback exato no log do servidor.
"""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.logging_config import (
    RequestIdFilter,
    describe_exception,
    get_request_id,
    set_request_id,
)
from core.middleware import RequestContextMiddleware


class ErroComStatus(Exception):
    def __init__(self, status_code, mensagem=""):
        super().__init__(mensagem)
        self.status_code = status_code


# ------------------------------------------------------- describe_exception


def test_descricao_nunca_vem_vazia():
    """Vários SDKs levantam exceção com str() vazio; o app receberia '' no erro."""
    assert describe_exception(RuntimeError()) == "RuntimeError"


def test_descricao_inclui_tipo_e_status():
    texto = describe_exception(ErroComStatus(429, "quota exceeded"))
    assert "ErroComStatus" in texto
    assert "429" in texto
    assert "quota exceeded" in texto


def test_descricao_sem_status_usa_so_tipo_e_texto():
    assert describe_exception(ValueError("ticker inválido")) == (
        "ValueError · ticker inválido"
    )


# ------------------------------------------------------------- request_id


def test_request_id_default_sem_contexto():
    set_request_id("fixo")
    assert get_request_id() == "fixo"


def test_request_id_gerado_tem_tamanho_util():
    rid = set_request_id()
    assert len(rid) == 12
    assert rid.isalnum()


async def test_request_id_nao_vaza_entre_tarefas():
    """Duas requisições simultâneas não podem compartilhar o id."""
    vistos = []

    async def tarefa(nome):
        set_request_id(nome)
        await asyncio.sleep(0)  # cede o controle para a outra tarefa
        vistos.append((nome, get_request_id()))

    await asyncio.gather(tarefa("aaa"), tarefa("bbb"))

    assert vistos == [("aaa", "aaa"), ("bbb", "bbb")] or vistos == [
        ("bbb", "bbb"),
        ("aaa", "aaa"),
    ]


def test_filtro_injeta_request_id_no_registro():
    set_request_id("abc123")
    registro = logging.LogRecord(
        "teste", logging.INFO, __file__, 1, "msg", None, None
    )

    assert RequestIdFilter().filter(registro) is True
    assert registro.request_id == "abc123"


# ------------------------------------------------------------- middleware


def montar_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/eco")
    def eco():
        return {"request_id": get_request_id()}

    @app.get("/explode")
    def explode():
        raise RuntimeError("falha proposital")

    return app


def test_header_de_resposta_traz_o_request_id():
    with TestClient(montar_app()) as client:
        r = client.get("/eco")

    assert r.status_code == 200
    assert r.headers["x-request-id"] == r.json()["request_id"]


def test_request_id_do_cliente_e_respeitado():
    """Permite rastrear a mesma operação do app até o log da API."""
    with TestClient(montar_app()) as client:
        r = client.get("/eco", headers={"X-Request-ID": "vindo-do-app"})

    assert r.json()["request_id"] == "vindo-do-app"
    assert r.headers["x-request-id"] == "vindo-do-app"


def test_ids_diferentes_entre_requisicoes():
    with TestClient(montar_app()) as client:
        primeiro = client.get("/eco").json()["request_id"]
        segundo = client.get("/eco").json()["request_id"]

    assert primeiro != segundo


def test_excecao_nao_tratada_e_logada_com_request_id(caplog):
    caplog.set_level(logging.ERROR, logger="api.access")
    client = TestClient(montar_app(), raise_server_exceptions=False)

    with client:
        r = client.get("/explode")

    assert r.status_code == 500
    registros = [x for x in caplog.records if "ERRO NAO TRATADO" in x.getMessage()]
    assert registros, "a exceção precisa aparecer no log de acesso"
    assert registros[0].exc_info is not None, "o traceback precisa ir junto"
