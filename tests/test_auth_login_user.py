import uuid
from datetime import date
from unittest.mock import MagicMock

from api import auth_router
from core.security import get_password_hash
from models.user import User


def test_login_returns_user_without_password(monkeypatch):
    user = User(
        id=uuid.uuid4(), name="Ana", email="ana@x.com", password_hash=get_password_hash("segredo123"),
        birth_date=date(1990, 1, 1), investor_profile="MODERATE", is_active=True,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    form = MagicMock(username="ana@x.com", password="segredo123")

    res = auth_router.login_for_access_token(form_data=form, db=db)

    assert res["token_type"] == "bearer" and res["access_token"]
    dumped = res["user"].model_dump(mode="json")
    assert dumped["email"] == "ana@x.com" and dumped["investor_profile"] == "MODERATE"
    assert "password_hash" not in dumped and "password" not in dumped
