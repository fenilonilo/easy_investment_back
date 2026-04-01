import json
import asyncio
import yfinance as yf
from fastapi import HTTPException
from typing import List, Optional
from models.asset import Asset, AssetQuote
from infrastructure.cache import ICacheProvider
from fastapi.concurrency import run_in_threadpool
from infrastructure.providers import IAssetProvider


class AssetService:
    def __init__(self, provider: IAssetProvider, cache: ICacheProvider):
        self.provider = provider
        self.cache = cache

    async def get_asset_quote(self, ticker: str) -> AssetQuote:
        ticker_upper = ticker.upper()
        cache_key = f"quote_{ticker_upper}"

        # 1. Tenta buscar no Redis
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            # Pydantic v1 usa parse_raw, v2 usa model_validate_json
            return AssetQuote.parse_raw(cached_data)

        # 2. Se não tem no cache, busca na API externa (Preço/Dados)
        try:
            quote = await self.provider.get_quote(ticker_upper)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        # 3. Integração da Lógica de Ícone (Yahoo Finance)
        try:
            # Criamos o objeto Ticker
            ticker_yf = yf.Ticker(ticker_upper)

            # .info é síncrono e lento, rodamos em threadpool
            info = await run_in_threadpool(lambda: ticker_yf.info)
            site = info.get('website')

            if site:
                dominio = site.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                quote.icon_url = f"https://www.google.com/s2/favicons?domain={dominio}&sz=128"
            else:
                # Fallback automático se não houver site
                clean_ticker = ticker_upper.split('.')[0]
                quote.icon_url = f"https://logo.clearbit.com/{clean_ticker}.com"

        except Exception as e:
            print(f"Erro ao buscar logo para {ticker_upper}: {e}")
            # Garantimos que ao menos o objeto quote tenha algo no icon_url
            quote.icon_url = f"https://logo.clearbit.com/{ticker_upper.split('.')[0]}.com"

        # 4. Salva no Redis (Cache)
        # quote.json() no Pydantic v1, quote.model_dump_json() no v2
        await self.cache.set(cache_key, quote.json())

        return quote


    async def search_assets(self, query: Optional[str]) -> List[Asset]:
        cache_key = f"search_{query or 'default'}"

        # 1. Busca no Redis
        cached = await self.cache.get(cache_key)
        if cached:
            return [Asset(**i) for i in json.loads(cached)]

        # 2. Busca no Provider (Yahoo Global Search)
        # Assume-se que 'assets' aqui já são instâncias de Asset ou compatíveis
        assets = await self.provider.get_available_assets(query)

        # 3. Função auxiliar para processar cada ícone individualmente
        async def fetch_icon(asset: Asset):
            try:
                # yf.Ticker() é rápido, mas .info faz a chamada de rede lenta
                ticker_yf = yf.Ticker(asset.ticker)

                # Rodamos o .info em uma thread separada para não bloquear o loop de eventos
                info = await run_in_threadpool(lambda: ticker_yf.info)
                site = info.get('website')

                if site:
                    # Limpa o domínio para o favicon
                    dominio = site.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                    asset.icon_url = f"https://www.google.com/s2/favicons?domain={dominio}&sz=128"
                else:
                    # Fallback baseado no tipo (ajuste conforme os campos reais do seu objeto)
                    asset_type = getattr(asset, 'type', 'EQUITY')
                    if asset_type == "EQUITY":
                        clean_ticker = asset.ticker.split('.')[0]
                        asset.icon_url = f"https://logo.clearbit.com/{clean_ticker}.com"
                    else:
                        asset.icon_url = None
            except Exception as e:
                # Log de erro silencioso para não quebrar a resposta principal
                print(f"Erro ao buscar logo para {asset.ticker}: {e}")
                asset.icon_url = None
            return asset

        # 4. Execução Paralela: Dispara as buscas de todos os ativos simultaneamente
        # Em vez de levar (N * tempo_de_um), levará apenas o tempo do mais lento.
        if assets:
            await asyncio.gather(*(fetch_icon(asset) for asset in assets))

        # 5. Salva no Redis por 1 hora (usa .model_dump() se estiver no Pydantic v2, ou .dict() no v1)
        # Se houver erro de compatibilidade, use: [a.dict() if hasattr(a, 'dict') else a.model_dump() for a in assets]
        assets_data = [a.model_dump() if hasattr(a, 'model_dump') else a.dict() for a in assets]
        await self.cache.set(cache_key, json.dumps(assets_data), ttl=3600)

        print(f"Assets found with logos: {len(assets)} items")
        return assets

    async def _get_with_cache(self, key: str, ttl: int, fetch_func):
        cached = await self.cache.get(key)
        if cached:
            return cached  # Retorna string JSON para o router parsear ou pydantic usar

        data = await fetch_func()
        # Se for uma lista de objetos Pydantic, converte para JSON
        json_data = json.dumps([i.dict() for i in data]) if isinstance(data, list) else data.json()
        await self.cache.set(key, json_data, ttl=ttl)
        return json_data

    async def get_history(self, ticker: str, period: str):
        return await self._get_with_cache(
            f"hist_{ticker}_{period}", 3600,  # Cache 1 hora
            lambda: self.provider.get_history(ticker, period, "1d")
        )

    async def get_financial_summary(self, ticker: str):
        return await self._get_with_cache(
            f"fin_{ticker}", 86400,  # Cache 24 horas (balanços mudam pouco)
            lambda: self.provider.get_financials(ticker)
        )

    async def get_dividends(self, ticker: str):
        return await self._get_with_cache(
            f"div_{ticker}", 86400,
            lambda: self.provider.get_dividends(ticker)
        )

    async def get_news(self, ticker: str):
        return await self._get_with_cache(
            f"news_{ticker}", 1800,  # Cache 30 min
            lambda: self.provider.get_news(ticker)
        )