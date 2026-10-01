"""Orquestração do chat: rodar o agente, streamar e gerenciar sessões."""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from agno.db.base import SessionType
from agno.run.agent import RunEvent
from agno.run.base import RunStatus

from core.config import LOG_MESSAGE_PREVIEW_CHARS
from core.logging_config import describe_exception, get_request_id
from infrastructure.ai.model_router import ModelProvider, is_availability_error
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


# Tools que gravam no banco: depois que uma delas roda, repetir a run em outro
# modelo poderia executar a escrita duas vezes.
_TOOLS_COM_EFEITO = {"adicionar_a_watchlist", "remover_da_watchlist"}

MSG_INDISPONIVEL = "Serviço de IA temporariamente indisponível, tente novamente."
MSG_COTA = "Limite de uso do serviço de IA atingido no momento, tente novamente em instantes."
MSG_GENERICA = "Não foi possível gerar a resposta agora, tente novamente."
MSG_SEM_DETALHE = "O modelo interrompeu a geração sem informar o motivo."


def mensagem_usuario(exc: BaseException) -> str:
    """Texto seguro para o app; o erro cru do provider fica só no log."""
    if not is_availability_error(exc):
        return MSG_GENERICA
    texto = describe_exception(exc).lower()
    if any(m in texto for m in ("429", "quota", "resource_exhausted", "rate limit")):
        return MSG_COTA
    return MSG_INDISPONIVEL


class AgentUnavailable(Exception):
    """Nenhum provider de IA conseguiu responder.

    `str()` é a mensagem para o usuário; o erro técnico fica em `.raw`.
    """

    def __init__(self, mensagem: str, raw: Optional[str] = None):
        super().__init__(mensagem)
        self.raw = raw or mensagem


def _indisponivel(exc: BaseException) -> AgentUnavailable:
    return AgentUnavailable(mensagem_usuario(exc), describe_exception(exc))


# O Agno injeta perfil/watchlist na mensagem do usuário; isso é para o modelo, não
# para o histórico que o app exibe.
_CONTEXTO_INJETADO = re.compile(r"\s*<additional context>.*?</additional context>", re.DOTALL)


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
            conteudo = getattr(message, "content", None)
            if isinstance(conteudo, str):
                conteudo = _CONTEXTO_INJETADO.sub("", conteudo)
            mensagens.append(
                {
                    "role": getattr(message, "role", None),
                    "content": conteudo,
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

    @staticmethod
    async def _arun(agent, message: str, session_id: str, user_ctx: UserContext):
        """`arun` sem stream não levanta quando o modelo falha: o Agno devolve um
        RunOutput com status ERROR e o texto do erro em `content`. Sem converter,
        o app recebe 200 com o JSON do provider como se fosse a resposta.
        """
        run_output = await agent.arun(
            message, session_id=session_id, user_id=user_ctx.user_id
        )
        if getattr(run_output, "status", None) == RunStatus.error:
            texto = str(getattr(run_output, "content", "") or "") or MSG_SEM_DETALHE
            logger.error("chat: run terminou com status ERROR | motivo=%s", texto)
            if _TOOLS_COM_EFEITO.intersection(_tool_names(run_output)):
                # Uma escrita já rodou: não dá para repetir em outro modelo.
                raise AgentUnavailable(MSG_GENERICA, texto)
            raise RuntimeError(texto)
        return run_output

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
            run_output = await self._arun(agent, message, session_id, user_ctx)
        except AgentUnavailable:
            raise
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
                raise _indisponivel(exc) from exc

            provider = fallback
            agent = await self._build_agent(provider, user_ctx, session_id)
            try:
                run_output = await self._arun(agent, message, session_id, user_ctx)
            except AgentUnavailable:
                raise
            except Exception as fallback_exc:
                logger.exception(
                    "chat: fallback %s TAMBÉM falhou | session=%s | erro=%s",
                    provider.value,
                    session_id,
                    describe_exception(fallback_exc),
                )
                raise _indisponivel(fallback_exc) from fallback_exc

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

        Os eventos ficam em buffer até a "decisão": o primeiro token ou uma tool
        com efeito colateral. Falha antes disso (exceção OU evento `run_error`,
        que é como o Agno reporta 503/429 com stream_events=True) troca de
        provider e recomeça, e o `start` sai uma vez só, com o provider final.
        Depois da decisão, recomeçar faria o cliente receber duas respostas
        concatenadas — então uma falha vira um frame `error` e o stream fecha,
        sem `done` (que pareceria uma resposta vazia bem-sucedida).
        """
        if session_id:
            await self.assert_can_use_session(session_id, user_ctx.user_id)
        else:
            session_id = str(uuid4())

        provider = await self.runtime.model_router.pick()
        request_id = get_request_id()
        inicio = time.perf_counter()

        logger.info(
            "stream iniciado | user=%s session=%s provider=%s | msg=%s",
            user_ctx.user_id,
            session_id,
            provider.value,
            _preview(message),
        )

        trocou = False
        while True:
            agent = await self._build_agent(provider, user_ctx, session_id)
            buffer: List[Any] = []
            partes: List[str] = []
            tools_vistas: List[str] = []
            decidido = False
            erro_no_meio: Optional[str] = None
            falha_previa: Optional[BaseException] = None

            try:
                # Sem await: com stream=True o arun devolve um async generator,
                # não uma coroutine. Awaitar levanta TypeError.
                async for evento in agent.arun(
                    message,
                    session_id=session_id,
                    user_id=user_ctx.user_id,
                    stream=True,
                    stream_events=True,
                ):
                    nome = getattr(evento, "event", None)
                    if nome == RunEvent.run_error.value:
                        texto = str(getattr(evento, "content", "") or "")
                        if not decidido:
                            logger.error(
                                "stream: provider %s falhou antes do primeiro token "
                                "(run_error) | session=%s | motivo=%s",
                                provider.value,
                                session_id,
                                texto or "sem detalhe do provider",
                            )
                            falha_previa = RuntimeError(texto or MSG_SEM_DETALHE)
                            break
                        erro_no_meio = texto or MSG_SEM_DETALHE
                        logger.error(
                            "stream: o modelo %s abortou no meio da geração | "
                            "session=%s | %s chars já emitidos | motivo=%s",
                            getattr(agent.model, "id", "?"),
                            session_id,
                            len("".join(partes)),
                            erro_no_meio,
                        )
                        yield self._frame_erro(
                            RuntimeError(erro_no_meio), session_id, request_id
                        )
                        continue

                    if decidido:
                        for frame in _frames_do_evento(evento, partes, tools_vistas):
                            yield frame
                        continue

                    buffer.append(evento)
                    if _decide(evento):
                        decidido = True
                        yield self._start(session_id, provider, agent)
                        for ev in buffer:
                            for frame in _frames_do_evento(ev, partes, tools_vistas):
                                yield frame
                        buffer = []
            except Exception as exc:
                if decidido:
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
                logger.exception(
                    "stream: provider %s falhou antes do primeiro token | session=%s | erro=%s",
                    provider.value,
                    session_id,
                    describe_exception(exc),
                )
                falha_previa = exc

            if falha_previa is not None:
                fallback = (
                    None
                    if trocou
                    else await self.runtime.model_router.fallback_for(
                        provider, falha_previa
                    )
                )
                if fallback is None:
                    yield self._frame_erro(falha_previa, session_id, request_id)
                    return
                provider, trocou = fallback, True
                continue

            break

        if not decidido:
            # Run vazia (ou só eventos de controle): ainda abre e fecha o stream.
            logger.warning(
                "stream: %s terminou sem token nem tool | session=%s",
                provider.value,
                session_id,
            )
            yield self._start(session_id, provider, agent)
            for ev in buffer:
                for frame in _frames_do_evento(ev, partes, tools_vistas):
                    yield frame
        elif trocou:
            logger.info(
                "stream: fallback para %s deu certo | session=%s", provider.value, session_id
            )

        conteudo = "".join(partes)
        duracao = (time.perf_counter() - inicio) * 1000
        if erro_no_meio:
            logger.warning(
                "stream encerrado com erro parcial | session=%s em %.0fms | %s chars",
                session_id,
                duracao,
                len(conteudo),
            )
            return  # o frame `error` já saiu; `done` pareceria sucesso
        logger.info(
            "stream concluído | session=%s provider=%s em %.0fms | %s chars | tools=%s",
            session_id,
            provider.value,
            duracao,
            len(conteudo),
            tools_vistas or "nenhuma",
        )
        if not conteudo.strip():
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
    def _start(session_id: str, provider: ModelProvider, agent) -> str:
        return _sse(
            "start",
            {
                "session_id": session_id,
                "provider": provider.value,
                "model": getattr(agent.model, "id", ""),
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
                "detail": mensagem_usuario(exc),
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

    return []


def _decide(evento: Any) -> bool:
    """Evento a partir do qual não dá mais para trocar de provider."""
    nome = getattr(evento, "event", None)
    if nome == RunEvent.run_content.value:
        conteudo = getattr(evento, "content", None)
        return isinstance(conteudo, str) and bool(conteudo)
    if nome == RunEvent.tool_call_started.value:
        tool = getattr(evento, "tool", None)
        return getattr(tool, "tool_name", None) in _TOOLS_COM_EFEITO
    return False
