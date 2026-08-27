"""Objetos caros do subsistema de IA, criados uma vez no lifespan da aplicação.

O resto do projeto constrói dependências por request (`api/asset_router.py`
cria um `RedisCache()` novo a cada chamada). Para o agente isso não serve: o
banco do Agno, o pool do pgvector e os clientes dos modelos precisam
sobreviver entre requisições.

O `Knowledge` é a exceção: construí-lo abre conexão com o Postgres de forma
síncrona (`Knowledge.__post_init__` chama `vector_db.exists()`/`create()`).
Fazer isso no lifespan travaria o boot da API inteira sempre que o
`postgres_ai` estivesse fora do ar — e derrubaria também os endpoints de
ativos, que não têm nada a ver com IA. Então ele é construído sob demanda, em
threadpool, e a falha é tolerada: sem knowledge o agente perde o RAG mas
continua respondendo com as tools de mercado e o histórico.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from agno.db.postgres import AsyncPostgresDb
from agno.knowledge.knowledge import Knowledge
from starlette.concurrency import run_in_threadpool

from infrastructure.ai.agent_db import build_agent_db
from infrastructure.ai.knowledge import build_knowledge
from infrastructure.ai.model_router import ModelRouter
from infrastructure.cache import ICacheProvider, RedisCache

logger = logging.getLogger(__name__)

# Quanto tempo esperar antes de tentar construir o Knowledge de novo depois de
# uma falha. Sem isso, com o postgres_ai fora do ar, cada mensagem de chat
# esperaria o timeout de conexão inteiro antes de responder.
_KNOWLEDGE_RETRY_SECONDS = 60


@dataclass
class AIRuntime:
    db: AsyncPostgresDb
    model_router: ModelRouter
    cache: ICacheProvider

    _knowledge: Optional[Knowledge] = None
    _knowledge_failed_at: Optional[float] = None
    _contagem_avisada: bool = False
    _knowledge_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get_knowledge(self) -> Optional[Knowledge]:
        """Knowledge memoizado, ou None se o pgvector não estiver acessível."""
        if self._knowledge is not None:
            return self._knowledge
        if self._em_backoff():
            logger.debug("Knowledge em backoff; respondendo sem RAG")
            return None

        async with self._knowledge_lock:
            # Outra corrotina pode ter resolvido isso enquanto esperávamos.
            if self._knowledge is not None:
                return self._knowledge
            if self._em_backoff():
                return None

            inicio = time.monotonic()
            try:
                self._knowledge = await run_in_threadpool(build_knowledge, self.db)
            except Exception:
                self._knowledge_failed_at = time.monotonic()
                logger.warning(
                    "Knowledge base indisponível; o agente vai responder SEM RAG. "
                    "Confira se o postgres_ai está no ar (docker compose ps). "
                    "Nova tentativa em %ss.",
                    _KNOWLEDGE_RETRY_SECONDS,
                    exc_info=True,
                )
                return None

            self._knowledge_failed_at = None
            logger.info(
                "Knowledge base conectada em %.0fms", (time.monotonic() - inicio) * 1000
            )
            await self._avisar_se_vazia()
            return self._knowledge

    async def _avisar_se_vazia(self) -> None:
        """Traduz o 'Found 0 documents' do agno em instrução acionável.

        Sem isso, um knowledge base que nunca foi ingerido se comporta como um
        que funciona: o agente responde, só que sem nenhuma fonte, e a única
        pista no log é uma linha do agno que não diz o que fazer.
        """
        if self._knowledge is None or self._contagem_avisada:
            return
        self._contagem_avisada = True
        try:
            _, total = await self._knowledge.aget_content(limit=1, page=1)
        except Exception:
            logger.debug("Não foi possível contar os conteúdos do knowledge", exc_info=True)
            return

        if not total:
            logger.warning(
                "Knowledge base VAZIA (0 documentos). O agente vai responder sem "
                "consultar as explicações de métricas, e o agno vai logar "
                "'Found 0 documents' a cada busca. Rode: "
                "uv run python scripts/ingest_knowledge.py"
            )
        else:
            logger.info("Knowledge base com %s documento(s) ingerido(s)", total)

    def _em_backoff(self) -> bool:
        if self._knowledge_failed_at is None:
            return False
        return (time.monotonic() - self._knowledge_failed_at) < _KNOWLEDGE_RETRY_SECONDS

    async def aclose(self) -> None:
        engines = [getattr(self.db, "db_engine", None)]
        if self._knowledge is not None:
            engines.append(getattr(self._knowledge.vector_db, "db_engine", None))

        for engine in engines:
            dispose = getattr(engine, "dispose", None)
            if dispose is None:
                continue
            try:
                result = dispose()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.warning("Falha ao fechar um engine do subsistema de IA", exc_info=True)


def build_ai_runtime() -> AIRuntime:
    """Só objetos sem I/O — seguro de chamar no lifespan."""
    cache = RedisCache()
    return AIRuntime(
        db=build_agent_db(),
        model_router=ModelRouter(cache),
        cache=cache,
    )
