"""Orquestração do chat: rodar o agente, streamar e gerenciar sessões."""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from agno.db.base import SessionType
from agno.run.agent import RunEvent

from core.config import LOG_MESSAGE_PREVIEW_CHARS
from core.logging_config import describe_exception, get_request_id
from infrastructure.ai.model_router import ModelProvider
from infrastructure.ai.runtime import AIRuntime
from services.ai.agent_factory import build_agent
from services.ai.context import UserContext
from services.asset_service import AssetService

logger = logging.getLogger(__name__)


def _preview(texto: str) -> str:
    """Trecho da mensagem para o log, sem despejar a conversa inteira."""
    if LOG_MESSAGE_PREVIEW_CHARS <= 0:
        return f"<{len(texto)} chars>"
    limpo = " ".join(texto.split())
    if len(limpo) <= LOG_MESSAGE_PREVIEW_CHARS:
        return limpo
    return limpo[:LOG_MESSAGE_PREVIEW_CHARS] + "…"


class SessionNotFound(Exception):
    """A sessão não existe ou não pertence a quem pediu.

    Os dois casos viram o mesmo erro de propósito: distinguir "não existe" de
    "é de outra pessoa" já entregaria a informação de que aquele id é válido.
    """


class AgentUnavailable(Exception):
    """Nenhum provider de IA conseguiu responder."""


@dataclass
class ChatResult:
    session_id: str
    run_id: Optional[str]
    content: str
    model_used: str
    provider: str
    tools_used: List[str]


def _tool_names(run_output: Any) -> List[str]:
    nomes: List[str] = []
    for tool in getattr(run_output, "tools", None) or []:
        nome = getattr(tool, "tool_name", None) or (
            tool.get("tool_name") if isinstance(tool, dict) else None
        )
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def _sse(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class AIChatService:
    def __init__(self, runtime: AIRuntime, asset_service: AssetService):
        self.runtime = runtime
        self.asset_service = asset_service

    # ------------------------------------------------------------------
    # Sessões
    # ------------------------------------------------------------------

    async def assert_can_use_session(self, session_id: str, user_id: str) -> None:
        """Bloqueia retomar a conversa de outra pessoa.

        Sem esta checagem, mandar um `session_id` alheio em `POST /ai/chat`
        carregaria o histórico do dono dele para dentro do contexto do modelo.
        A busca aqui é DE PROPÓSITO sem filtro de `user_id`: com o filtro, uma
        sessão de terceiro voltaria como `None` e seria confundida com uma
        sessão nova — e aí seria criada por cima.
        """
        session = await self.runtime.db.get_session(
            session_id=session_id, session_type=SessionType.AGENT
        )
        if session is None:
            return  # id ainda não usado: será uma sessão nova
        if getattr(session, "user_id", None) != user_id:
            raise SessionNotFound(session_id)

    async def _get_owned_session(self, session_id: str, user_id: str):
        session = await self.runtime.db.get_session(
            session_id=session_id, session_type=SessionType.AGENT, user_id=user_id
        )
        if session is None:
            raise SessionNotFound(session_id)
        return session

    async def list_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        sessions = await self.runtime.db.get_sessions(
            session_type=SessionType.AGENT,
            user_id=user_id,
            limit=limit,
            sort_by="updated_at",
            sort_order="desc",
        )
        resultado = []
        for session in sessions or []:
            summary = getattr(session, "summary", None)
            resultado.append(
                {
                    "session_id": session.session_id,
                    "created_at": getattr(session, "created_at", None),
                    "updated_at": getattr(session, "updated_at", None),
                    "runs_count": len(getattr(session, "runs", None) or []),
                    "summary": getattr(summary, "summary", None),
                    "topics": getattr(summary, "topics", None) or [],
                }
            )
        return resultado

    async def get_session_messages(
        self, session_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        session = await self._get_owned_session(session_id, user_id)
        mensagens = []
        for message in session.get_chat_history() or []:
            mensagens.append(
                {
                    "role": getattr(message, "role", None),
                    "content": getattr(message, "content", None),
                    "created_at": getattr(message, "created_at", None),
                }
            )
        return mensagens

    async def get_session_summary(
        self, session_id: str, user_id: str
    ) -> Dict[str, Any]:
        session = await self._get_owned_session(session_id, user_id)
        summary = session.get_session_summary()
        return {
            "session_id": session_id,
            "summary": getattr(summary, "summary", None),
            "topics": getattr(summary, "topics", None) or [],
            "updated_at": getattr(summary, "updated_at", None),
        }

    async def delete_session(self, session_id: str, user_id: str) -> None:
        # Confirma a posse antes: `delete_session` devolve False tanto para
        # "não existe" quanto para "é de outro", sem distinguir.
        await self._get_owned_session(session_id, user_id)
        await self.runtime.db.delete_session(session_id=session_id, user_id=user_id)

    # ------------------------------------------------------------------
    # Conversa
    # ------------------------------------------------------------------

    async def _build_agent(
        self, provider: ModelProvider, user_ctx: UserContext, session_id: str
    ):
        return build_agent(
            runtime=self.runtime,
            asset_service=self.asset_service,
            user_ctx=user_ctx,
            model=self.runtime.model_router.build(provider),
            session_id=session_id,
            knowledge=await self.runtime.get_knowledge(),
        )

    async def chat(
        self, user_ctx: UserContext, message: str, session_id: Optional[str] = None
    ) -> ChatResult:
        if session_id:
            await self.assert_can_use_session(session_id, user_ctx.user_id)
        else:
            # Geramos o id em vez de deixar o Agno gerar, para poder devolvê-lo
            # na resposta mesmo que a run falhe no meio.
            session_id = str(uuid4())

        provider = await self.runtime.model_router.pick()
        inicio = time.perf_counter()
        logger.info(
            "chat iniciado | user=%s session=%s provider=%s | msg=%s",
            user_ctx.user_id,
            session_id,
            provider.value,
            _preview(message),
        )

        try:
            agent = await self._build_agent(provider, user_ctx, session_id)
            run_output = await agent.arun(
                message, session_id=session_id, user_id=user_ctx.user_id
            )
        except Exception as exc:
            # exception() antes de qualquer coisa: o traceback original é a
            # única pista real, e AgentUnavailable(str(exc)) o descartaria.
            logger.exception(
                "chat: provider %s falhou | session=%s | erro=%s",
                provider.value,
                session_id,
                describe_exception(exc),
            )
            fallback = await self.runtime.model_router.fallback_for(provider, exc)
            if fallback is None:
                raise AgentUnavailable(describe_exception(exc)) from exc

            provider = fallback
            agent = await self._build_agent(provider, user_ctx, session_id)
            try:
                run_output = await agent.arun(
                    message, session_id=session_id, user_id=user_ctx.user_id
                )
            except Exception as fallback_exc:
                logger.exception(
                    "chat: fallback %s TAMBÉM falhou | session=%s | erro=%s",
                    provider.value,
                    session_id,
                    describe_exception(fallback_exc),
                )
                raise AgentUnavailable(
                    describe_exception(fallback_exc)
                ) from fallback_exc

        tools = _tool_names(run_output)
        conteudo = run_output.get_content_as_string()
        logger.info(
            "chat concluído | session=%s provider=%s em %.0fms | %s chars | tools=%s",
            session_id,
            provider.value,
            (time.perf_counter() - inicio) * 1000,
            len(conteudo),
            tools or "nenhuma",
        )
        if not conteudo.strip():
            # Resposta vazia chega no app como bolha em branco e vira
            # "a IA deu erro", sem nada no log que explique.
            logger.warning(
                "chat: o modelo %s devolveu conteúdo VAZIO | session=%s | "
                "verifique filtro de segurança ou limite de tokens do provider",
                getattr(agent.model, "id", "?"),
                session_id,
            )

        return ChatResult(
            session_id=run_output.session_id or session_id,
            run_id=getattr(run_output, "run_id", None),
            content=conteudo,
            model_used=getattr(agent.model, "id", ""),
            provider=provider.value,
            tools_used=tools,
        )

    async def stream(
        self, user_ctx: UserContext, message: str, session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Frames SSE: `start`, `token`, `tool`, `done` e `error`.

        A troca de provider só acontece antes do primeiro evento. Depois que o
        primeiro token saiu, recomeçar em outro modelo faria o cliente receber
        duas respostas concatenadas — então uma falha no meio vira um frame
        `error` e o stream fecha.
        """
        if session_id:
            await self.assert_can_use_session(session_id, user_ctx.user_id)
        else:
            session_id = str(uuid4())

        provider = await self.runtime.model_router.pick()
        agent = await self._build_agent(provider, user_ctx, session_id)
        request_id = get_request_id()
        inicio = time.perf_counter()

        logger.info(
            "stream iniciado | user=%s session=%s provider=%s | msg=%s",
            user_ctx.user_id,
            session_id,
            provider.value,
            _preview(message),
        )

        primeiro_evento = None
        iterador = None
        try:
            # Sem await: com stream=True o arun devolve um async generator,
            # não uma coroutine. Awaitar levanta TypeError.
            iterador = agent.arun(
                message,
                session_id=session_id,
                user_id=user_ctx.user_id,
                stream=True,
                stream_events=True,
            ).__aiter__()
            primeiro_evento = await iterador.__anext__()
        except StopAsyncIteration:
            logger.warning(
                "stream: %s abriu e fechou sem emitir nenhum evento | session=%s",
                provider.value,
                session_id,
            )
            iterador = None
        except Exception as exc:
            logger.exception(
                "stream: provider %s falhou antes do primeiro token | session=%s | erro=%s",
                provider.value,
                session_id,
                describe_exception(exc),
            )
            fallback = await self.runtime.model_router.fallback_for(provider, exc)
            if fallback is None:
                yield self._frame_erro(exc, session_id, request_id)
                return
            provider = fallback
            agent = await self._build_agent(provider, user_ctx, session_id)
            try:
                iterador = agent.arun(
                    message,
                    session_id=session_id,
                    user_id=user_ctx.user_id,
                    stream=True,
                    stream_events=True,
                ).__aiter__()
                primeiro_evento = await iterador.__anext__()
                logger.info(
                    "stream: fallback para %s deu certo | session=%s",
                    provider.value,
                    session_id,
                )
            except StopAsyncIteration:
                iterador = None
            except Exception as fallback_exc:
                logger.exception(
                    "stream: fallback %s TAMBÉM falhou | session=%s | erro=%s",
                    provider.value,
                    session_id,
                    describe_exception(fallback_exc),
                )
                yield self._frame_erro(fallback_exc, session_id, request_id)
                return

        yield _sse(
            "start",
            {
                "session_id": session_id,
                "provider": provider.value,
                "model": getattr(agent.model, "id", ""),
            },
        )

        partes: List[str] = []
        tools_vistas: List[str] = []
        erro_no_meio: Optional[str] = None
        try:
            if primeiro_evento is not None:
                for frame in _frames_do_evento(primeiro_evento, partes, tools_vistas):
                    yield frame
            if iterador is not None:
                async for evento in iterador:
                    if getattr(evento, "event", None) == RunEvent.run_error.value:
                        erro_no_meio = str(getattr(evento, "content", "") or "")
                        logger.error(
                            "stream: o modelo %s abortou no meio da geração | "
                            "session=%s | %s chars já emitidos | motivo=%s",
                            getattr(agent.model, "id", "?"),
                            session_id,
                            len("".join(partes)),
                            erro_no_meio or "sem detalhe do provider",
                        )
                    for frame in _frames_do_evento(evento, partes, tools_vistas):
                        yield frame
        except Exception as exc:
            logger.exception(
                "stream: falha DURANTE a geração | session=%s provider=%s | "
                "%s chars já emitidos | erro=%s",
                session_id,
                provider.value,
                len("".join(partes)),
                describe_exception(exc),
            )
            yield self._frame_erro(exc, session_id, request_id)
            return

        conteudo = "".join(partes)
        duracao = (time.perf_counter() - inicio) * 1000
        if erro_no_meio:
            logger.warning(
                "stream encerrado com erro parcial | session=%s em %.0fms | %s chars",
                session_id,
                duracao,
                len(conteudo),
            )
        else:
            logger.info(
                "stream concluído | session=%s provider=%s em %.0fms | %s chars | tools=%s",
                session_id,
                provider.value,
                duracao,
                len(conteudo),
                tools_vistas or "nenhuma",
            )
        if not conteudo.strip() and not erro_no_meio:
            logger.warning(
                "stream: nenhum token gerado pelo modelo %s | session=%s | o app vai "
                "receber uma resposta vazia; verifique filtro de segurança do provider",
                getattr(agent.model, "id", "?"),
                session_id,
            )

        yield _sse(
            "done",
            {
                "session_id": session_id,
                "provider": provider.value,
                "model": getattr(agent.model, "id", ""),
                "content": conteudo,
            },
        )

    @staticmethod
    def _frame_erro(exc: BaseException, session_id: str, request_id: str) -> str:
        """Frame de erro que o app consegue reportar e a gente consegue achar.

        O `request_id` vai junto de propósito: é o que permite pegar o print do
        usuário e localizar o traceback exato no log do servidor.
        """
        return _sse(
            "error",
            {
                "detail": describe_exception(exc),
                "session_id": session_id,
                "request_id": request_id,
            },
        )


def _frames_do_evento(
    evento: Any, partes: List[str], tools_vistas: Optional[List[str]] = None
) -> List[str]:
    """Traduz um evento do Agno em zero ou mais frames SSE."""
    nome = getattr(evento, "event", None)

    if nome == RunEvent.run_content.value:
        conteudo = getattr(evento, "content", None)
        if isinstance(conteudo, str) and conteudo:
            partes.append(conteudo)
            return [_sse("token", {"content": conteudo})]
        return []

    if nome == RunEvent.tool_call_started.value:
        tool = getattr(evento, "tool", None)
        tool_name = getattr(tool, "tool_name", None)
        logger.info("stream: tool acionada -> %s", tool_name or "?")
        if tools_vistas is not None and tool_name and tool_name not in tools_vistas:
            tools_vistas.append(tool_name)
        return [_sse("tool", {"name": tool_name})]

    if nome == RunEvent.tool_call_error.value:
        tool = getattr(evento, "tool", None)
        logger.error(
            "stream: tool %s FALHOU | %s",
            getattr(tool, "tool_name", "?"),
            getattr(tool, "tool_call_error", None)
            or getattr(evento, "content", None)
            or "sem detalhe",
        )
        return []

    if nome == RunEvent.run_error.value:
        # O log detalhado sai no chamador, que tem session_id e contexto.
        return [
            _sse(
                "error",
                {
                    "detail": str(getattr(evento, "content", "") or "")
                    or "O modelo interrompeu a geração sem informar o motivo.",
                    "request_id": get_request_id(),
                },
            )
        ]

    return []
