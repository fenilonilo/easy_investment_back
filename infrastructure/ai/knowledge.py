"""Knowledge base RAG sobre métricas e avaliação de ativos financeiros.

Vetores no pgvector, catálogo de conteúdos no mesmo Postgres do Agno.
Embeddings pelo Gemini — a Groq não expõe API de embeddings, então quando o
Gemini está fora do ar a busca no knowledge degrada mas o agente continua
funcionando com as tools de mercado e o histórico.

Atenção: `Knowledge.__post_init__` chama `vector_db.exists()` e, se preciso,
`vector_db.create()`. Ou seja, **construir um `Knowledge` abre conexão com o
Postgres de forma síncrona e bloqueante**. Por isso o runtime constrói este
objeto sob demanda, dentro de threadpool, e não no import nem no lifespan.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from agno.db.base import AsyncBaseDb, BaseDb
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

from core.config import (
    AI_DATABASE_URL,
    AI_DB_SCHEMA,
    AI_VECTOR_TABLE,
    GEMINI_EMBEDDER_DIMENSIONS,
    GEMINI_EMBEDDER_ID,
    GOOGLE_API_KEY,
)

KNOWLEDGE_NAME = "Base de Conhecimento Financeiro"
KNOWLEDGE_DESCRIPTION = (
    "Explicações de métricas de mercado, indicadores fundamentalistas, métodos "
    "de valuation, análise de risco e critérios para avaliar um ativo."
)

# Sem isto o psycopg fica preso no connect por minutos quando o postgres_ai
# está fora do ar, e cada request do chat pendura um worker junto.
_CONNECT_TIMEOUT_SECONDS = 5


def build_embedder() -> GeminiEmbedder:
    return GeminiEmbedder(
        id=GEMINI_EMBEDDER_ID,
        dimensions=GEMINI_EMBEDDER_DIMENSIONS,
        api_key=GOOGLE_API_KEY,
    )


def build_vector_engine() -> Engine:
    return create_engine(
        AI_DATABASE_URL,
        connect_args={"connect_timeout": _CONNECT_TIMEOUT_SECONDS},
        pool_pre_ping=True,
    )


def build_vector_db() -> PgVector:
    return PgVector(
        table_name=AI_VECTOR_TABLE,
        schema=AI_DB_SCHEMA,
        db_engine=build_vector_engine(),
        embedder=build_embedder(),
        # Híbrida = vetorial + full-text. O full-text precisa saber o idioma
        # para o stemming; o default do Agno é "english" e estragaria a busca
        # por termos como "dividendos"/"endividamento".
        search_type=SearchType.hybrid,
        content_language="portuguese",
    )


def build_knowledge(contents_db: BaseDb | AsyncBaseDb | None = None) -> Knowledge:
    """Constrói o Knowledge. BLOQUEANTE: conecta no Postgres e cria o schema."""
    return Knowledge(
        name=KNOWLEDGE_NAME,
        description=KNOWLEDGE_DESCRIPTION,
        vector_db=build_vector_db(),
        contents_db=contents_db,
    )
