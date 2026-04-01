import yfinance as yf
import asyncio
import httpx
from abc import ABC, abstractmethod
from models.asset import Asset, AssetQuote, HistoryPoint, Dividend, Financials, NewsItem
from typing import List, Optional


class IAssetProvider(ABC):
    @abstractmethod
    async def get_quote(self, ticker: str) -> AssetQuote: pass

    @abstractmethod
    async def get_available_assets(self, query: str) -> List[Asset]: pass

    @abstractmethod
    async def get_history(self, ticker: str, period: str, interval: str) -> List[HistoryPoint]: pass

    @abstractmethod
    async def get_dividends(self, ticker: str) -> List[Dividend]: pass

    @abstractmethod
    async def get_financials(self, ticker: str) -> Financials: pass

    @abstractmethod
    async def get_news(self, ticker: str) -> List[NewsItem]: pass


class YahooFinanceProvider(IAssetProvider):
    """
    Implementação completa utilizando yfinance e busca global do Yahoo.
    """

    def _format_ticker(self, ticker: str) -> str:
        ticker = ticker.upper()
        if len(ticker) >= 5 and ticker[-1].isdigit():
            return f"{ticker}.SA"
        elif ticker in ["BTC", "ETH", "SOL", "USDC", "USDT"]:
            return f"{ticker}-USD"
        return ticker

    async def _get_ticker_object(self, ticker: str):
        search_ticker = self._format_ticker(ticker)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: yf.Ticker(search_ticker))

    async def get_quote(self, ticker: str) -> AssetQuote:
        stock = await self._get_ticker_object(ticker)
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: stock.info)

        if not info or 'regularMarketPrice' not in info:
            raise ValueError(f"Ativo {ticker} não encontrado")

        price = info.get('regularMarketPrice') or info.get('previousClose', 0)
        open_price = info.get('regularMarketOpen') or price
        change = ((price - open_price) / open_price * 100) if open_price else 0

        icon_url = info.get('logo_url')
        if not icon_url and info.get('website'):
            domain = info.get('website').replace('https://', '').replace('http://', '').split('/')[0]
            icon_url = f"https://logo.clearbit.com/{domain}"

        return AssetQuote(
            ticker=ticker.upper(),
            name=info.get('shortName') or info.get('longName') or ticker,
            icon_url=icon_url or "",
            price_usd=float(price),
            direction="subindo" if change > 0 else "caindo" if change < 0 else "estável"
        )

    async def get_available_assets(self, query: str) -> List[Asset]:
        search_query = query if query else "P"
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={search_query}"
        headers = {'User-Agent': 'Mozilla/5.0'}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                data = response.json()
                assets = []
                for item in data.get("quotes", []):
                    ticker = item.get("symbol")
                    assets.append(Asset(
                        ticker=ticker,
                        name=item.get("shortname") or ticker,
                        icon_url=f"https://logo.clearbit.com/{ticker.split('.')[0]}.com"
                    ))
                return assets
            except Exception:
                return []

    async def get_history(self, ticker: str, period: str = "1mo", interval: str = "1d") -> List[HistoryPoint]:
        stock = await self._get_ticker_object(ticker)
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: stock.history(period=period, interval=interval))
        return [HistoryPoint(date=str(index.date()), close=row['Close']) for index, row in df.iterrows()]

    async def get_dividends(self, ticker: str) -> List[Dividend]:
        stock = await self._get_ticker_object(ticker)
        loop = asyncio.get_event_loop()
        divs = await loop.run_in_executor(None, lambda: stock.dividends)
        return [Dividend(date=str(index.date()), amount=float(value)) for index, value in divs.tail(10).items()]

    async def get_financials(self, ticker: str) -> Financials:
        stock = await self._get_ticker_object(ticker)
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: stock.info)
        return Financials(
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            dividend_yield=info.get("dividendYield"),
            target_price=info.get("targetMeanPrice"),
            recommendation=info.get("recommendationKey")
        )

    async def get_news(self, ticker: str) -> List[NewsItem]:
        stock = await self._get_ticker_object(ticker)
        loop = asyncio.get_event_loop()
        news = await loop.run_in_executor(None, lambda: stock.news)

        if not news:
            return []

        news_list = []
        for n in news[:5]:
            # Acessamos a sub-chave 'content'
            content = n.get('content', {})

            # Extraímos os dados com segurança
            title = content.get('title', 'Sem título')
            summary = content.get('summary') or content.get('description') or ""
            link = content.get('canonicalUrl', {}).get('url', '')
            publisher = content.get('provider', {}).get('displayName', 'Yahoo Finance')
            publish_time = content.get('pubDate', '')

            news_list.append(NewsItem(
                title=title,
                summary=summary,  # Mapeando o resumo
                link=link,
                publisher=publisher,
                provider_publish_time=publish_time
            ))

        return news_list