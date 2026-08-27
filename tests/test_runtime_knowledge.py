"""Construção tolerante do Knowledge.

`Knowledge.__post_init__` conecta no Postgres de forma bloqueante. Com o
postgres_ai fora do ar isso demora dezenas de segundos, então a falha precisa
ser lembrada — senão cada mensagem de chat paga o timeout de novo.
"""

import asyncio
from types import SimpleNamespace

from infrastructure.ai import runtime as runtime_mod
from infrastructure.ai.runtime import AIRuntime


def montar():
    return AIRuntime(
        db=SimpleNamespace(),
        model_router=SimpleNamespace(),
        cache=SimpleNamespace(),
    )


async def test_constroi_e_memoiza(monkeypatch):
    chamadas = []
    fake = object()
    monkeypatch.setattr(
        runtime_mod, "build_knowledge", lambda db: (chamadas.append(db), fake)[1]
    )
    rt = montar()

    assert await rt.get_knowledge() is fake
    assert await rt.get_knowledge() is fake
    assert len(chamadas) == 1, "só pode construir uma vez"


async def test_falha_devolve_none_sem_propagar(monkeypatch):
    def explode(db):
        raise OSError("connection timeout expired")

    monkeypatch.setattr(runtime_mod, "build_knowledge", explode)
    rt = montar()

    assert await rt.get_knowledge() is None


async def test_nao_retenta_dentro_do_backoff(monkeypatch):
    """O ponto do teste: o agente responde rápido mesmo com o pgvector fora."""
    chamadas = []

    def explode(db):
        chamadas.append(1)
        raise OSError("connection timeout expired")

    monkeypatch.setattr(runtime_mod, "build_knowledge", explode)
    rt = montar()

    for _ in range(5):
        assert await rt.get_knowledge() is None

    assert len(chamadas) == 1


async def test_retenta_depois_do_backoff(monkeypatch):
    chamadas = []
    fake = object()

    def build(db):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise OSError("connection timeout expired")
        return fake

    monkeypatch.setattr(runtime_mod, "build_knowledge", build)
    monkeypatch.setattr(runtime_mod, "_KNOWLEDGE_RETRY_SECONDS", 0)
    rt = montar()

    assert await rt.get_knowledge() is None
    assert await rt.get_knowledge() is fake
    assert len(chamadas) == 2


async def test_chamadas_concorrentes_constroem_uma_vez_so(monkeypatch):
    chamadas = []
    fake = object()

    def build(db):
        chamadas.append(1)
        return fake

    monkeypatch.setattr(runtime_mod, "build_knowledge", build)
    rt = montar()

    resultados = await asyncio.gather(*(rt.get_knowledge() for _ in range(10)))

    assert all(r is fake for r in resultados)
    assert len(chamadas) == 1
