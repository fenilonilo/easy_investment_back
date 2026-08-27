"""Banco do Agno: sessões de chat, resumos e catálogo do knowledge base.

Aponta para o `postgres_ai` (pgvector), separado do easy_finace. O Agno cria e
migra as próprias tabelas — por isso este subsistema não depende do Alembic,
que o projeto não tem.
"""

from agno.db.postgres import AsyncPostgresDb

from core.config import (
    AI_DATABASE_URL,
    AI_DB_SCHEMA,
    AI_KNOWLEDGE_TABLE,
    AI_SESSION_TABLE,
)


def build_agent_db() -> AsyncPostgresDb:
    return AsyncPostgresDb(
        db_url=AI_DATABASE_URL,
        db_schema=AI_DB_SCHEMA,
        session_table=AI_SESSION_TABLE,
        knowledge_table=AI_KNOWLEDGE_TABLE,
    )
