"""Escolha de modelo com fallback Gemini -> Groq.

O Gemini é o modelo principal. Quando ele estoura cota ou fica indisponível,
o roteador grava uma flag de quarentena no Redis (com TTL) e passa a devolver
a Groq direto, sem nem tentar o Gemini, até a flag expirar.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

from agno.models.base import Model
from agno.models.google import Gemini
from agno.models.groq import Groq

from core.logging_config import describe_exception
from core.config import (
    AI_FALLBACK_COOLDOWN_SECONDS,
    GEMINI_MODEL_ID,
    GOOGLE_API_KEY,
    GROQ_API_KEY,
    GROQ_MODEL_ID,
    GROQ_REASONING_EFFORT,
)
from infrastructure.cache import ICacheProvider

logger = logging.getLogger(__name__)

GEMINI_COOLDOWN_KEY = "ai:gemini_cooldown"

# Códigos HTTP que significam "o provider não está te atendendo agora".
_AVAILABILITY_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# Trechos de mensagem que indicam cota/indisponibilidade nos SDKs do Google e da
# Groq. Comparados em minúsculas contra o str() da exceção.
_AVAILABILITY_MESSAGE_MARKERS = (
    "resource_exhausted",
    "resource exhausted",
    "quota",
    "rate limit",
    "rate_limit",
    "too many requests",
    "overloaded",
    "unavailable",
    "service is currently",
    "deadline exceeded",
    "timeout",
    "timed out",
    "internal error",
    "bad gateway",
)

# Trechos que indicam erro de configuração/entrada. Esses NUNCA disparam
# fallback: trocar de modelo não conserta uma chave inválida, e mascarar o erro
# faria a API responder normalmente enquanto o Gemini está permanentemente
# quebrado.
_PERMANENT_MESSAGE_MARKERS = (
    "api key not valid",
    "api_key_invalid",
    "invalid api key",
    "permission denied",
    "permission_denied",
    "unauthenticated",
    "unauthorized",
)


class ModelProvider(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"


def _status_code_of(exc: BaseException) -> Optional[int]:
    for attr in ("status_code", "code", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def is_availability_error(exc: BaseException) -> bool:
    """True quando vale a pena repetir a chamada em outro provider.

    Erros de credencial/permissão retornam False de propósito: eles precisam
    estourar para o usuário em vez de serem silenciosamente contornados.
    """
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True

    message = str(exc).lower()
    if any(marker in message for marker in _PERMANENT_MESSAGE_MARKERS):
        return False

    status = _status_code_of(exc)
    if status is not None:
        if status in _AVAILABILITY_STATUS_CODES:
            return True
        # 4xx que não seja 408/429 é problema da requisição, não do provider.
        if 400 <= status < 500:
            return False

    return any(marker in message for marker in _AVAILABILITY_MESSAGE_MARKERS)


class ModelRouter:
    """Decide qual modelo usar e mantém a quarentena do Gemini no Redis."""

    def __init__(
        self,
        cache: ICacheProvider,
        *,
        gemini_model_id: str = GEMINI_MODEL_ID,
        groq_model_id: str = GROQ_MODEL_ID,
        google_api_key: Optional[str] = GOOGLE_API_KEY,
        groq_api_key: Optional[str] = GROQ_API_KEY,
        cooldown_seconds: int = AI_FALLBACK_COOLDOWN_SECONDS,
        groq_reasoning_effort: Optional[str] = GROQ_REASONING_EFFORT,
    ):
        self.cache = cache
        self.gemini_model_id = gemini_model_id
        self.groq_model_id = groq_model_id
        self.google_api_key = google_api_key
        self.groq_api_key = groq_api_key
        self.cooldown_seconds = cooldown_seconds
        self.groq_reasoning_effort = groq_reasoning_effort

        # Instâncias reaproveitadas entre requests: construir um Model novo por
        # request criaria um pool de conexões HTTP novo a cada mensagem.
        self._models: dict[ModelProvider, Model] = {}

    @property
    def has_gemini(self) -> bool:
        return bool(self.google_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    def build(self, provider: ModelProvider) -> Model:
        cached = self._models.get(provider)
        if cached is not None:
            return cached

        if provider is ModelProvider.GEMINI:
            model: Model = Gemini(id=self.gemini_model_id, api_key=self.google_api_key)
        else:
            request_params = (
                {"reasoning_effort": self.groq_reasoning_effort}
                if self.groq_reasoning_effort
                else None
            )
            model = Groq(
                id=self.groq_model_id,
                api_key=self.groq_api_key,
                request_params=request_params,
            )

        self._models[provider] = model
        return model

    async def _gemini_in_cooldown(self) -> bool:
        try:
            return await self.cache.get(GEMINI_COOLDOWN_KEY) is not None
        except Exception:
            # Redis fora do ar não pode derrubar o chat: sem flag legível,
            # seguimos com o modelo principal.
            logger.warning("Falha ao ler a quarentena do Gemini no Redis", exc_info=True)
            return False

    async def pick(self) -> ModelProvider:
        """Provider a usar nesta tentativa."""
        if not self.has_gemini:
            if not self.has_groq:
                raise RuntimeError(
                    "Nenhum provider de IA configurado: defina GOOGLE_API_KEY e/ou GROQ_API_KEY."
                )
            return ModelProvider.GROQ

        if self.has_groq and await self._gemini_in_cooldown():
            return ModelProvider.GROQ

        return ModelProvider.GEMINI

    async def mark_gemini_unavailable(self) -> None:
        """Coloca o Gemini de quarentena pelo tempo de cooldown."""
        try:
            await self.cache.set(GEMINI_COOLDOWN_KEY, "1", ttl=self.cooldown_seconds)
        except Exception:
            logger.warning("Falha ao gravar a quarentena do Gemini no Redis", exc_info=True)

    async def fallback_for(
        self, provider: ModelProvider, exc: BaseException
    ) -> Optional[ModelProvider]:
        """Provider alternativo para repetir a chamada, ou None se não houver.

        Só existe fallback saindo do Gemini, por erro de disponibilidade, com a
        Groq configurada. Cada recusa é logada com o motivo — sem isso, "o
        agente falhou e não trocou de modelo" vira adivinhação.
        """
        detalhe = describe_exception(exc)

        if provider is not ModelProvider.GEMINI:
            logger.error(
                "Falha na Groq (último recurso), sem fallback disponível | erro=%s",
                detalhe,
            )
            return None

        if not self.has_groq:
            logger.error(
                "Gemini falhou e GROQ_API_KEY não está configurada, sem fallback | erro=%s",
                detalhe,
            )
            return None

        if not is_availability_error(exc):
            logger.error(
                "Gemini falhou por erro NÃO transitório (credencial ou requisição "
                "inválida): trocar de modelo não resolveria, o erro sobe | erro=%s",
                detalhe,
            )
            return None

        await self.mark_gemini_unavailable()
        logger.warning(
            "Gemini indisponível, caindo para a Groq (%s) e colocando o Gemini "
            "em quarentena por %ss | erro=%s",
            self.groq_model_id,
            self.cooldown_seconds,
            detalhe,
        )
        return ModelProvider.GROQ
