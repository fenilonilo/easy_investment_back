from fastapi import FastAPI
from api import auth_router, asset_router, profile_router, user_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="🚀 API Financeira Pro",
    description="""
    API para consulta de ativos financeiros, criptomoedas e stocks americanas.

    ## Endpoints Principais:
    * **Search**: Busca global de ativos.
    * **Quote**: Preço e tendência em tempo real.
    * **History**: Dados para construção de gráficos.
    * **News**: Notícias com resumo e fonte.
    * **Dividends**: Histórico de proventos.
    """,
    version="1.0.0",
    contact={
        "name": "Seu Nome",
        "url": "http://seu-link-ou-github.com",
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Registra os roteadores separados
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(profile_router.router)
app.include_router(asset_router.router)

