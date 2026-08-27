"""Tools do agente sobre os dados da própria API.

Complementam o `YFinanceTools` com duas coisas que só existem aqui: os dados já
cacheados no Redis pelo `AssetService` (mesma resposta que os endpoints REST
devolvem) e a watchlist do usuário.

Todas as tools de banco abrem a própria sessão via `SessionLocal`. Usar a
sessão do request não serviria: uma tool pode ser executada de dentro do
gerador de streaming, que continua vivo depois do request ter terminado.
"""

import json
import logging
import time
from typing import Any, Callable, List
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified
from starlette.concurrency import run_in_threadpool

from core.logging_config import describe_exception
from infrastructure.database import SessionLocal
from models.user import UserWatchlist
from services.asset_service import AssetService

logger = logging.getLogger(__name__)


def _parse(payload: Any) -> Any:
    """Normaliza o retorno do `AssetService` para algo serializável.

    Ele devolve string JSON em `get_history`/`get_financials`/`get_dividends`/
    `get_news`, objeto Pydantic em `get_asset_quote` e lista de objetos em
    `search_assets` — os três casos precisam ser tratados.
    """
    if isinstance(payload, str):
        return json.loads(payload)
    if isinstance(payload, (list, tuple)):
        return [_parse(item) for item in payload]
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    return payload


async def _executar(nome: str, alvo: str, coro) -> str:
    """Roda uma tool logando entrada, duração e falha.

    O agno engole a exceção de uma tool e devolve o erro ao modelo, que
    costuma seguir a conversa como se nada tivesse acontecido. Sem este log,
    "a IA respondeu errado sobre a PETR4" não tem como ser investigado.
    """
    inicio = time.perf_counter()
    try:
        dados = _parse(await coro)
    except Exception as exc:
        logger.exception("tool %s(%s) FALHOU | erro=%s", nome, alvo, describe_exception(exc))
        # Devolvido ao modelo: melhor ele dizer que não conseguiu o dado do
        # que inventar um número.
        return json.dumps(
            {"erro": f"Não foi possível obter os dados de {alvo}.", "tool": nome},
            ensure_ascii=False,
        )

    resultado = json.dumps(dados, ensure_ascii=False)
    vazio = not dados or (isinstance(dados, (list, dict)) and len(dados) == 0)
    logger.info(
        "tool %s(%s) ok em %.0fms | %s chars%s",
        nome,
        alvo,
        (time.perf_counter() - inicio) * 1000,
        len(resultado),
        " | RESULTADO VAZIO" if vazio else "",
    )
    return resultado


# --------------------------------------------------------------------------
# Leitura de mercado (via AssetService, aproveitando o cache do Redis)
# --------------------------------------------------------------------------


def build_asset_tools(service: AssetService) -> List[Callable]:
    async def cotacao_atual(ticker: str) -> str:
        """Cotação atual de um ativo, com nome e direção do movimento.

        Aceita o ticker como o usuário escreve (PETR4, AAPL, BTC); a formatação
        para o padrão do Yahoo (.SA, -USD) é automática.

        Args:
            ticker: Código do ativo. Ex.: "PETR4", "AAPL", "BTC".
        """
        return await _executar(
            "cotacao_atual", ticker, service.get_asset_quote(ticker)
        )

    async def historico_precos(ticker: str, periodo: str = "1mo") -> str:
        """Série histórica de preços de fechamento de um ativo.

        Args:
            ticker: Código do ativo. Ex.: "PETR4", "AAPL".
            periodo: Janela do histórico: "1d", "5d", "1mo", "3mo", "6mo",
                "1y", "2y", "5y", "10y", "ytd" ou "max". Padrão "1mo".
        """
        return await _executar(
            "historico_precos",
            f"{ticker},{periodo}",
            service.get_history(ticker, periodo),
        )

    async def resumo_financeiro(ticker: str) -> str:
        """Indicadores fundamentalistas do ativo (dados de balanço e múltiplos).

        Args:
            ticker: Código do ativo. Ex.: "PETR4", "AAPL".
        """
        return await _executar(
            "resumo_financeiro", ticker, service.get_financial_summary(ticker)
        )

    async def historico_dividendos(ticker: str) -> str:
        """Histórico de proventos pagos pelo ativo, com data e valor.

        Args:
            ticker: Código do ativo. Ex.: "PETR4", "ITSA4".
        """
        return await _executar(
            "historico_dividendos", ticker, service.get_dividends(ticker)
        )

    async def noticias_do_ativo(ticker: str) -> str:
        """Notícias recentes sobre o ativo, com título, fonte e resumo.

        Args:
            ticker: Código do ativo. Ex.: "PETR4", "AAPL".
        """
        return await _executar("noticias_do_ativo", ticker, service.get_news(ticker))

    async def buscar_ativos(termo: str) -> str:
        """Busca ativos por nome ou código quando o ticker exato é desconhecido.

        Args:
            termo: Texto da busca. Ex.: "petrobras", "vale", "apple".
        """
        return await _executar("buscar_ativos", termo, service.search_assets(termo))

    return [
        cotacao_atual,
        historico_precos,
        resumo_financeiro,
        historico_dividendos,
        noticias_do_ativo,
        buscar_ativos,
    ]


# --------------------------------------------------------------------------
# Watchlist (leitura e escrita)
# --------------------------------------------------------------------------


def load_watchlist_sync(user_id: UUID) -> List[dict]:
    """Tickers da watchlist do usuário. Roda em threadpool — SQLAlchemy é sync."""
    db = SessionLocal()
    try:
        watchlist = (
            db.query(UserWatchlist).filter(UserWatchlist.user_id == user_id).first()
        )
        return list(watchlist.tickers or []) if watchlist else []
    finally:
        db.close()


async def load_watchlist(user_id: UUID) -> List[dict]:
    return await run_in_threadpool(load_watchlist_sync, user_id)


def _add_ticker_sync(user_id: UUID, ticker: str, nome: str) -> str:
    db = SessionLocal()
    try:
        watchlist = (
            db.query(UserWatchlist).filter(UserWatchlist.user_id == user_id).first()
        )
        entrada = {"ticker": ticker, "name": nome or ticker, "icon_url": ""}

        if watchlist is None:
            db.add(UserWatchlist(user_id=user_id, tickers=[entrada]))
            db.commit()
            return f"{ticker} adicionado à watchlist."

        atuais = list(watchlist.tickers or [])
        if any(item.get("ticker") == ticker for item in atuais):
            return f"{ticker} já estava na watchlist; nada foi alterado."

        atuais.append(entrada)
        watchlist.tickers = atuais
        # JSONB não rastreia mutação in-place — sem isto o commit não persiste.
        flag_modified(watchlist, "tickers")
        db.commit()
        return f"{ticker} adicionado à watchlist."
    finally:
        db.close()


def _remove_ticker_sync(user_id: UUID, ticker: str) -> str:
    db = SessionLocal()
    try:
        watchlist = (
            db.query(UserWatchlist).filter(UserWatchlist.user_id == user_id).first()
        )
        if watchlist is None or not watchlist.tickers:
            return "A watchlist está vazia; não há o que remover."

        restantes = [
            item for item in watchlist.tickers if item.get("ticker") != ticker
        ]
        if len(restantes) == len(watchlist.tickers):
            return f"{ticker} não está na watchlist."

        watchlist.tickers = restantes
        flag_modified(watchlist, "tickers")
        db.commit()
        return f"{ticker} removido da watchlist."
    finally:
        db.close()


def build_watchlist_tools(user_id: UUID) -> List[Callable]:
    """Tools de watchlist presas ao usuário autenticado.

    O `user_id` vem do JWT e fica capturado no closure — o modelo não tem como
    informá-lo, então não há como o agente ler ou alterar a lista de outra
    pessoa nem sob prompt injection.
    """

    async def adicionar_a_watchlist(ticker: str, nome: str = "") -> str:
        """Adiciona um ativo à watchlist do usuário. Use só quando ele pedir.

        Args:
            ticker: Código do ativo a adicionar. Ex.: "PETR4".
            nome: Nome da empresa/ativo, se você souber. Ex.: "Petrobras PN".
        """
        ticker_normalizado = ticker.strip().upper()
        if not ticker_normalizado:
            logger.warning("tool adicionar_a_watchlist chamada com ticker vazio")
            return "Ticker inválido."
        try:
            resultado = await run_in_threadpool(
                _add_ticker_sync, user_id, ticker_normalizado, nome.strip()
            )
        except Exception as exc:
            logger.exception(
                "tool adicionar_a_watchlist(%s) FALHOU | user=%s | erro=%s",
                ticker_normalizado,
                user_id,
                describe_exception(exc),
            )
            return f"Não consegui alterar a watchlist agora ({ticker_normalizado})."
        logger.info(
            "tool adicionar_a_watchlist(%s) | user=%s | %s",
            ticker_normalizado,
            user_id,
            resultado,
        )
        return resultado

    async def remover_da_watchlist(ticker: str) -> str:
        """Remove um ativo da watchlist do usuário. Use só quando ele pedir.

        Args:
            ticker: Código do ativo a remover. Ex.: "PETR4".
        """
        ticker_normalizado = ticker.strip().upper()
        if not ticker_normalizado:
            logger.warning("tool remover_da_watchlist chamada com ticker vazio")
            return "Ticker inválido."
        try:
            resultado = await run_in_threadpool(
                _remove_ticker_sync, user_id, ticker_normalizado
            )
        except Exception as exc:
            logger.exception(
                "tool remover_da_watchlist(%s) FALHOU | user=%s | erro=%s",
                ticker_normalizado,
                user_id,
                describe_exception(exc),
            )
            return f"Não consegui alterar a watchlist agora ({ticker_normalizado})."
        logger.info(
            "tool remover_da_watchlist(%s) | user=%s | %s",
            ticker_normalizado,
            user_id,
            resultado,
        )
        return resultado

    return [adicionar_a_watchlist, remover_da_watchlist]
