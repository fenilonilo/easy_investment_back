import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from api import ai_router, auth_router, asset_router, profile_router, user_router
from fastapi.middleware.cors import CORSMiddleware

from core.logging_config import setup_logging
from core.middleware import RequestContextMiddleware
from infrastructure.ai.runtime import build_ai_runtime

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Sobe os objetos caros do agente uma vez, em vez de por request.

    O banco do Agno, o pool do pgvector e os clientes dos modelos precisam
    sobreviver entre requisições.
    """
    # Antes de tudo: sem isto, nenhum log do projeto aparece.
    setup_logging()

    app.state.ai_runtime = build_ai_runtime()
    router = app.state.ai_runtime.model_router
    logger.info(
        "Agente pronto | gemini=%s groq=%s | modelos: %s / %s",
        "ok" if router.has_gemini else "SEM CHAVE",
        "ok" if router.has_groq else "SEM CHAVE",
        router.gemini_model_id,
        router.groq_model_id,
    )
    if not router.has_gemini and not router.has_groq:
        logger.error(
            "Nenhuma chave de IA configurada: defina GOOGLE_API_KEY e/ou GROQ_API_KEY "
            "no .env. Todo request para /ai vai falhar com 502."
        )

    yield

    logger.info("Encerrando o runtime de IA")
    await app.state.ai_runtime.aclose()


app = FastAPI(
    lifespan=lifespan,
    title="🚀 API Financeira Pro",
    description="""
    API para consulta de ativos financeiros, criptomoedas e stocks americanas.

    ## Endpoints Principais:
    * **Search**: Busca global de ativos.
    * **Quote**: Preço e tendência em tempo real.
    * **History**: Dados para construção de gráficos.
    * **News**: Notícias com resumo e fonte.
    * **Dividends**: Histórico de proventos.
    * **AI**: Agente de chat para gestão e avaliação de ativos.
    """,
    version="1.0.0",
    contact={
        "name": "Felipe Nilo M. de Faria",
        "url": "https://github.com/fenilonilo",
    },
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Sem isto o navegador esconde o header do app, e o usuário não consegue
    # reportar o id que localiza o erro no log do servidor.
    expose_headers=["X-Request-ID"],
)
# Registra os roteadores separados
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(profile_router.router)
app.include_router(asset_router.router)
app.include_router(ai_router.router)

