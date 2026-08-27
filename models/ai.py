"""Schemas do agente de IA. Pydantic v2 (o lock pina 2.12.5)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Mensagem do usuário para o agente.",
    )
    session_id: Optional[str] = Field(
        None,
        description=(
            "Conversa a continuar. Omita para começar uma nova — o id da sessão "
            "criada volta na resposta."
        ),
    )


class ChatResponse(BaseModel):
    session_id: str
    run_id: Optional[str] = None
    content: str
    provider: str = Field(description="Provider que respondeu: 'gemini' ou 'groq'.")
    model_used: str
    tools_used: List[str] = Field(
        default_factory=list, description="Tools acionadas nesta resposta."
    )


class SessionInfo(BaseModel):
    session_id: str
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    runs_count: int = 0
    summary: Optional[str] = None
    topics: List[str] = Field(default_factory=list)


class MessageItem(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    created_at: Optional[int] = None


class SessionDetail(BaseModel):
    session_id: str
    messages: List[MessageItem] = Field(default_factory=list)


class SessionSummaryResponse(BaseModel):
    session_id: str
    summary: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None
