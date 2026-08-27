"""Fallback Gemini -> Groq: quando acontece e, principalmente, quando não deve."""

import asyncio

import pytest

from infrastructure.ai.model_router import (
    GEMINI_COOLDOWN_KEY,
    ModelProvider,
    ModelRouter,
    is_availability_error,
)


class FakeCache:
    """ICacheProvider em memória, sem TTL real."""

    def __init__(self, inicial=None):
        self.dados = dict(inicial or {})
        self.sets = []

    async def get(self, key):
        return self.dados.get(key)

    async def set(self, key, value, ttl=60):
        self.dados[key] = value
        self.sets.append((key, value, ttl))


class CacheQuebrado:
    async def get(self, key):
        raise ConnectionError("redis fora do ar")

    async def set(self, key, value, ttl=60):
        raise ConnectionError("redis fora do ar")


class ErroHTTP(Exception):
    def __init__(self, status_code, mensagem=""):
        super().__init__(mensagem or f"HTTP {status_code}")
        self.status_code = status_code


def router(cache=None, **kwargs):
    base = dict(google_api_key="chave-gemini", groq_api_key="chave-groq")
    base.update(kwargs)
    return ModelRouter(cache or FakeCache(), **base)


# ---------------------------------------------------------------- classificação


@pytest.mark.parametrize(
    "exc",
    [
        ErroHTTP(429),
        ErroHTTP(503),
        ErroHTTP(500),
        ErroHTTP(408),
        Exception("429 RESOURCE_EXHAUSTED: quota exceeded"),
        Exception("The model is overloaded. Please try again later."),
        Exception("503 Service Unavailable"),
        asyncio.TimeoutError(),
        ConnectionError("connection reset"),
    ],
)
def test_erros_de_disponibilidade_sao_reconhecidos(exc):
    assert is_availability_error(exc) is True


@pytest.mark.parametrize(
    "exc",
    [
        ErroHTTP(401, "unauthorized"),
        ErroHTTP(403, "permission denied"),
        ErroHTTP(400, "invalid argument"),
        Exception("API key not valid. Please pass a valid API key."),
        Exception("PERMISSION_DENIED: caller does not have permission"),
    ],
)
def test_erros_permanentes_nao_sao_de_disponibilidade(exc):
    assert is_availability_error(exc) is False


def test_429_com_mensagem_de_chave_invalida_nao_dispara_fallback():
    """A mensagem manda mais que o status: chave inválida nunca é contornável."""
    exc = ErroHTTP(429, "API key not valid")
    assert is_availability_error(exc) is False


# ---------------------------------------------------------------------- escolha


async def test_escolhe_gemini_quando_nao_ha_quarentena():
    assert await router().pick() is ModelProvider.GEMINI


async def test_escolhe_groq_quando_gemini_esta_de_quarentena():
    cache = FakeCache({GEMINI_COOLDOWN_KEY: "1"})
    assert await router(cache).pick() is ModelProvider.GROQ


async def test_ignora_quarentena_se_a_groq_nao_esta_configurada():
    """Sem Groq não há para onde cair — melhor tentar o Gemini que falhar seco."""
    cache = FakeCache({GEMINI_COOLDOWN_KEY: "1"})
    assert await router(cache, groq_api_key=None).pick() is ModelProvider.GEMINI


async def test_usa_groq_quando_so_ela_esta_configurada():
    assert await router(google_api_key=None).pick() is ModelProvider.GROQ


async def test_erra_quando_nenhum_provider_configurado():
    with pytest.raises(RuntimeError, match="Nenhum provider"):
        await router(google_api_key=None, groq_api_key=None).pick()


async def test_redis_fora_do_ar_nao_derruba_a_escolha():
    assert await router(CacheQuebrado()).pick() is ModelProvider.GEMINI


# --------------------------------------------------------------------- fallback


async def test_fallback_grava_quarentena_e_devolve_groq():
    cache = FakeCache()
    r = router(cache, cooldown_seconds=300)

    destino = await r.fallback_for(ModelProvider.GEMINI, ErroHTTP(429))

    assert destino is ModelProvider.GROQ
    assert cache.sets == [(GEMINI_COOLDOWN_KEY, "1", 300)]


async def test_sem_fallback_para_erro_permanente():
    cache = FakeCache()
    r = router(cache)

    destino = await r.fallback_for(
        ModelProvider.GEMINI, Exception("API key not valid. Please pass a valid API key.")
    )

    assert destino is None
    assert cache.sets == [], "chave inválida não pode colocar o Gemini de quarentena"


async def test_sem_fallback_saindo_da_groq():
    """A Groq é o último recurso: falhou nela, o erro sobe."""
    assert await router().fallback_for(ModelProvider.GROQ, ErroHTTP(429)) is None


async def test_sem_fallback_se_a_groq_nao_esta_configurada():
    r = router(groq_api_key=None)
    assert await r.fallback_for(ModelProvider.GEMINI, ErroHTTP(429)) is None


# ----------------------------------------------------------------- construção


def test_modelos_sao_reaproveitados_entre_chamadas():
    """Construir um Model novo por request abriria um pool HTTP por mensagem."""
    r = router()
    assert r.build(ModelProvider.GEMINI) is r.build(ModelProvider.GEMINI)


def test_build_usa_os_ids_configurados():
    r = router(gemini_model_id="gemini-x", groq_model_id="openai/gpt-oss-120b")
    assert r.build(ModelProvider.GEMINI).id == "gemini-x"
    assert r.build(ModelProvider.GROQ).id == "openai/gpt-oss-120b"
