import json
from fastapi import APIRouter, Depends
from typing import List, Optional
from models.asset import AssetQuote, HistoryPoint, Dividend, Financials, NewsItem, Asset
from core.security import get_current_user
from services.asset_service import AssetService
from infrastructure.cache import RedisCache
from infrastructure.providers import YahooFinanceProvider

router = APIRouter(prefix="/assets", tags=["Assets"], dependencies=[Depends(get_current_user)])

# Injeção de dependência local para o router
def get_asset_service():
    return AssetService(provider=YahooFinanceProvider(), cache=RedisCache())

@router.get("", response_model=List[Asset])
async def list_assets(
    search: Optional[str] = None,
    service: AssetService = Depends(get_asset_service),
):
    """
    Retorna a lista de ativos. Se 'search' for enviado, busca na base global do Yahoo.
    """
    return await service.search_assets(search)

@router.get("/{ticker}", response_model=AssetQuote)
async def get_asset(
    ticker: str,
    service: AssetService = Depends(get_asset_service),
):
    """Retorna os detalhes em tempo real de um ativo."""
    return await service.get_asset_quote(ticker)

@router.get("/{ticker}/history", response_model=List[HistoryPoint])
async def get_asset_history(ticker: str, period: str = "1mo", service: AssetService = Depends(get_asset_service)):
    data = await service.get_history(ticker, period)
    return json.loads(data)

@router.get("/{ticker}/financials", response_model=Financials)
async def get_asset_financials(ticker: str, service: AssetService = Depends(get_asset_service)):
    data = await service.get_financial_summary(ticker)
    return Financials.parse_raw(data)

@router.get("/{ticker}/dividends", response_model=List[Dividend])
async def get_asset_dividends(ticker: str, service: AssetService = Depends(get_asset_service)):
    data = await service.get_dividends(ticker)
    return json.loads(data)

@router.get("/{ticker}/news", response_model=List[NewsItem])
async def get_asset_news(ticker: str, service: AssetService = Depends(get_asset_service)):
    data = await service.get_news(ticker)
    return json.loads(data)