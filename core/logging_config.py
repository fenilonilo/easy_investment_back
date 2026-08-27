"""Configuração de logging da aplicação.

O uvicorn configura apenas os loggers dele (`uvicorn`, `uvicorn.error`,
`uvicorn.access`) e **não** mexe no logger raiz. Sem o que está aqui, todo
`logger.info(...)` do projeto é descartado silenciosamente e `logger.warning`
cai no `logging.lastResort`, que imprime sem timestamp e sem contexto.

Também instala o `request_id`: um identificador curto por requisição que
aparece em toda linha de log daquela requisição e é devolvido no header
`X-Request-ID` e nos corpos de erro. É ele que liga "o app mostrou erro" a
"esta é a exceção no servidor".
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

from core.config import LOG_FORMAT, LOG_LEVEL, LOG_LEVEL_LIBS

# ContextVar em vez de variável global: cada requisição roda na própria tarefa
# asyncio e enxerga só o próprio valor, mesmo com dezenas concorrentes.
_request_id: ContextVar[str] = ContextVar("request_id", default="-")

# Libs que falam demais no INFO. O agno loga "Found 0 documents" a cada busca
# no knowledge base, o httpx loga toda requisição HTTP do yfinance.
_LIBS_BARULHENTAS = (
    "agno",
    "httpx",
    "httpcore",
    "urllib3",
    "yfinance",
    "peewee",
    "google_genai",
    "groq",
)


def set_request_id(value: Optional[str] = None) -> str:
    """Define o id da requisição atual. Sem argumento, gera um novo."""
    rid = value or uuid.uuid4().hex[:12]
    _request_id.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    """Injeta o request_id em todo registro, inclusive os das libs."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class TextFormatter(logging.Formatter):
    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s.%03d"

    def format(self, record: logging.LogRecord) -> str:
        record.short_name = record.name.replace("services.", "").replace(
            "infrastructure.", ""
        )
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por registro, para agregadores de log."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """Configura o logger raiz. Chamar uma vez, no início do lifespan."""
    if LOG_FORMAT == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = TextFormatter(
            fmt="%(asctime)s | %(levelname)-7s | %(short_name)-28s | req=%(request_id)-12s | %(message)s"
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    # Remove handlers de execuções anteriores (--reload recarrega o módulo).
    for antigo in list(root.handlers):
        root.removeHandler(antigo)
    root.addHandler(handler)
    root.setLevel(LOG_LEVEL)

    for nome in _LIBS_BARULHENTAS:
        logging.getLogger(nome).setLevel(LOG_LEVEL_LIBS)

    # O uvicorn tem handler próprio; sem isto cada linha de acesso sai em
    # duplicata, uma pelo handler dele e outra pelo nosso.
    for nome in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(nome).propagate = False

    logging.getLogger(__name__).info(
        "Logging configurado | nivel=%s formato=%s libs=%s",
        LOG_LEVEL,
        LOG_FORMAT,
        LOG_LEVEL_LIBS,
    )


def describe_exception(exc: BaseException) -> str:
    """Descrição curta e sempre não-vazia de uma exceção.

    Vários SDKs levantam exceções cujo `str()` é vazio; `str(exc)` sozinho
    produziria uma mensagem de erro em branco tanto no log quanto no frame SSE
    entregue ao app.
    """
    texto = str(exc).strip()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    partes = [type(exc).__name__]
    if isinstance(status, int):
        partes.append(f"HTTP {status}")
    if texto:
        partes.append(texto)
    return " · ".join(partes)
