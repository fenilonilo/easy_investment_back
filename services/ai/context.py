"""Retrato imutável do usuário para o agente.

`get_current_user` devolve um `User` do SQLAlchemy preso à sessão do request
(`core/security.py:31`). Esse objeto fica destacado assim que a resposta é
enviada — e o gerador do streaming SSE continua rodando depois disso. Tocar
nele lá dentro daria `DetachedInstanceError`.

Por isso o agente nunca recebe o ORM: recebe este dataclass de tipos
primitivos, montado enquanto a sessão ainda está viva.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import UUID

PERFIS_LEGIVEIS = {
    "CONSERVATIVE": "conservador",
    "MODERATE": "moderado",
    "AGGRESSIVE": "arrojado",
}


@dataclass(frozen=True)
class UserContext:
    id: UUID
    name: str
    investor_profile: str
    watchlist: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def user_id(self) -> str:
        return str(self.id)

    @property
    def perfil_legivel(self) -> str:
        return PERFIS_LEGIVEIS.get(self.investor_profile, self.investor_profile)

    def as_dependencies(self) -> Dict[str, Any]:
        """O que o Agno injeta no contexto de cada mensagem."""
        return {
            "nome_do_usuario": self.name,
            "perfil_de_investidor": f"{self.investor_profile} ({self.perfil_legivel})",
            "watchlist": [
                {"ticker": item.get("ticker"), "nome": item.get("name")}
                for item in self.watchlist
                if item.get("ticker")
            ],
        }


def user_context_from_orm(user, watchlist: List[Dict[str, Any]]) -> UserContext:
    """Extrai os campos do ORM enquanto a sessão do request ainda está aberta."""
    return UserContext(
        id=user.id,
        name=user.name,
        investor_profile=user.investor_profile,
        watchlist=watchlist,
    )
