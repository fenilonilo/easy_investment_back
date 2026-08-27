"""Montagem do Agent do Agno para uma conversa específica."""

from typing import Optional

from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.models.base import Model
from agno.tools.yfinance import YFinanceTools

from core.config import AI_HISTORY_RUNS
from infrastructure.ai.runtime import AIRuntime
from services.ai.context import UserContext
from services.ai.prompts import AGENT_NAME, DESCRIPTION, INSTRUCTIONS
from services.ai.tools import build_asset_tools, build_watchlist_tools
from services.asset_service import AssetService

AGENT_ID = "consultor-de-ativos"


def build_agent(
    *,
    runtime: AIRuntime,
    asset_service: AssetService,
    user_ctx: UserContext,
    model: Model,
    session_id: Optional[str] = None,
    knowledge: Optional[Knowledge] = None,
) -> Agent:
    return Agent(
        id=AGENT_ID,
        name=AGENT_NAME,
        model=model,
        db=runtime.db,
        knowledge=knowledge,
        # Sem knowledge acessível não adianta oferecer a tool de busca.
        search_knowledge=knowledge is not None,
        tools=[
            YFinanceTools(all=True),
            *build_asset_tools(asset_service),
            *build_watchlist_tools(user_ctx.id),
        ],
        user_id=user_ctx.user_id,
        session_id=session_id,
        description=DESCRIPTION,
        instructions=INSTRUCTIONS,
        # Histórico: as últimas N interações vão inteiras para o contexto; o que
        # é mais antigo que isso chega resumido.
        add_history_to_context=True,
        num_history_runs=AI_HISTORY_RUNS,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
        # Watchlist e perfil entram como dependências resolvidas por run, então
        # acompanham sozinhas qualquer alteração feita entre uma mensagem e outra.
        dependencies=user_ctx.as_dependencies(),
        add_dependencies_to_context=True,
        markdown=True,
        telemetry=False,
    )
