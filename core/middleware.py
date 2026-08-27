"""Middleware de correlação e de log de acesso.

Middleware ASGI puro, e não `BaseHTTPMiddleware`: o `request_id` precisa estar
visível também enquanto o corpo da resposta é gerado. No streaming SSE o
gerador continua rodando bem depois de a resposta ter começado, e só o ASGI
puro mantém o mesmo contexto ativo durante essa fase.
"""

import logging
import time

from core.logging_config import set_request_id

logger = logging.getLogger("api.access")

# Barulho de health check e de documentação não precisa virar linha de log.
_ROTAS_SILENCIOSAS = {"/docs", "/openapi.json", "/redoc", "/favicon.ico"}


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Respeita o id que o cliente mandou, para rastrear app <-> API.
        entrada = None
        for chave, valor in scope.get("headers") or []:
            if chave == b"x-request-id":
                entrada = valor.decode("latin-1")[:64]
                break

        request_id = set_request_id(entrada)
        inicio = time.perf_counter()
        caminho = scope.get("path", "")
        metodo = scope.get("method", "")
        status_visto = {"code": 0}

        async def send_com_header(mensagem):
            if mensagem["type"] == "http.response.start":
                status_visto["code"] = mensagem["status"]
                headers = list(mensagem.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                mensagem = {**mensagem, "headers": headers}
            await send(mensagem)

        silenciosa = caminho in _ROTAS_SILENCIOSAS
        if not silenciosa:
            logger.info("--> %s %s", metodo, caminho)

        try:
            await self.app(scope, receive, send_com_header)
        except Exception:
            duracao = (time.perf_counter() - inicio) * 1000
            # Sem isto, uma exceção não tratada só apareceria no traceback do
            # uvicorn, sem o request_id que liga o erro ao relato do usuário.
            logger.exception(
                "<-- %s %s ERRO NAO TRATADO em %.0fms", metodo, caminho, duracao
            )
            raise

        duracao = (time.perf_counter() - inicio) * 1000
        if not silenciosa:
            status = status_visto["code"]
            nivel = logging.WARNING if status >= 400 else logging.INFO
            logger.log(
                nivel, "<-- %s %s %s em %.0fms", metodo, caminho, status, duracao
            )
