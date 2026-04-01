from abc import ABC, abstractmethod
from typing import Optional
import redis.asyncio as redis
from core.config import REDIS_URL, CACHE_TTL_SECONDS


class ICacheProvider(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]: pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int): pass


class RedisCache(ICacheProvider):
    def __init__(self):
        self.client = redis.from_url(REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS):
        await self.client.setex(key, ttl, value)