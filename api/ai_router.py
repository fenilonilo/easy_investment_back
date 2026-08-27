import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.logging_config import get_request_id
from core.security import get_current_user
from infrastructure.cache import RedisCache
from infrastructure.database import get_db
from infrastructure.providers import YahooFinanceProvider
from models.ai import (
    ChatRequest,
    ChatResponse,
    MessageItem,
    SessionDetail,
    SessionInfo,
    SessionSummaryResponse,
)
from models.user import User, UserWatchlist
from services.ai.chat_service import AgentUnavailable, AIChatService, SessionNotFound
from services.ai.context import UserContext, user_context_from_orm
from services.asset_service import AssetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(get_current_user)])


def _nao_encontrada(session_id: str, user_id: str) -> HTTPException:
    """404 padrão, já logando quem tentou acessar o quê."""
    logger.warning(
        "Sessão negada | session=%s user=%s (inexistente ou de outro usuário)",
        session_id,
        user_id,
    )
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada."
    )


def get_user_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserContext:
    """Retrato do usuário para o agente, montado com a sessão do request viva.

    Dependência síncrona de propósito: o Starlette a resolve em threadpool, e o
    SQLAlchemy deste projeto é síncrono (`infrastructure/database.py:7`).
    """
    watchlist = (
        db.query(UserWatchlist).filter(UserWatchlist.user_id == current_user.id).first()
    )
    tickers = list(watchlist.tickers or []) if watchlist else []
    return user_context_from_orm(current_user, tickers)


def get_chat_service(request: Request) -> AIChatService:
    # O runtime (banco do Agno, knowledge, clientes dos modelos) vem do lifespan;
    # só o AssetService é montado por request, como nos outros routers.
    return AIChatService(
        runtime=request.app.state.ai_runtime,
        asset_service=AssetService(provider=YahooFinanceProvider(), cache=RedisCache()),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: AIChatService = Depends(get_chat_service),
    user_ctx: UserContext = Depends(get_user_context),
):
    """Conversa com o agente e recebe a resposta completa de uma vez."""
    try:
        resultado = await service.chat(
            user_ctx=user_ctx, message=payload.message, session_id=payload.session_id
        )
    except SessionNotFound:
        raise _nao_encontrada(payload.session_id or "?", user_ctx.user_id)
    except AgentUnavailable as exc:
        # O traceback completo já foi logado no chat_service; aqui só ligamos
        # a resposta do app ao request_id que localiza aquele traceback.
        logger.error("Agente indisponível para user=%s | %s", user_ctx.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"O agente não conseguiu responder: {exc} "
                f"(request_id: {get_request_id()})"
            ),
        )

    return ChatResponse(
        session_id=resultado.session_id,
        run_id=resultado.run_id,
        content=resultado.content,
        provider=resultado.provider,
        model_used=resultado.model_used,
        tools_used=resultado.tools_used,
    )


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    service: AIChatService = Depends(get_chat_service),
    user_ctx: UserContext = Depends(get_user_context),
):
    """Mesma conversa, em SSE: eventos `start`, `token`, `tool`, `done`, `error`."""
    try:
        # Valida a posse antes de abrir o stream: uma vez que a resposta 200
        # começou, não dá mais para trocar o status para 404.
        if payload.session_id:
            await service.assert_can_use_session(payload.session_id, user_ctx.user_id)
    except SessionNotFound:
        raise _nao_encontrada(payload.session_id or "?", user_ctx.user_id)

    return StreamingResponse(
        service.stream(
            user_ctx=user_ctx, message=payload.message, session_id=payload.session_id
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(
    limit: int = 50,
    service: AIChatService = Depends(get_chat_service),
    user_ctx: UserContext = Depends(get_user_context),
):
    """Conversas do usuário autenticado, da mais recente para a mais antiga."""
    sessoes = await service.list_sessions(user_ctx.user_id, limit=limit)
    return [SessionInfo(**s) for s in sessoes]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    service: AIChatService = Depends(get_chat_service),
    user_ctx: UserContext = Depends(get_user_context),
):
    """Histórico completo de mensagens de uma conversa."""
    try:
        mensagens = await service.get_session_messages(session_id, user_ctx.user_id)
    except SessionNotFound:
        raise _nao_encontrada(session_id, user_ctx.user_id)
    return SessionDetail(
        session_id=session_id, messages=[MessageItem(**m) for m in mensagens]
    )


@router.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    service: AIChatService = Depends(get_chat_service),
    user_ctx: UserContext = Depends(get_user_context),
):
    """Resumo gerado da conversa, usado para dar contexto sem estourar o modelo."""
    try:
        resumo = await service.get_session_summary(session_id, user_ctx.user_id)
    except SessionNotFound:
        raise _nao_encontrada(session_id, user_ctx.user_id)
    return SessionSummaryResponse(**resumo)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    service: AIChatService = Depends(get_chat_service),
    user_ctx: UserContext = Depends(get_user_context),
):
    """Apaga uma conversa do usuário autenticado."""
    try:
        await service.delete_session(session_id, user_ctx.user_id)
    except SessionNotFound:
        raise _nao_encontrada(session_id, user_ctx.user_id)
