# /tests/unit/test_user_model.py
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.user import User, UserRoles, RegisterUserRequest


def make_user(**kwargs) -> User:
    data = dict(id=uuid4(), email='ivan@example.com', name='Иван', role=UserRoles.BUYER,
                created_at=datetime.now(timezone.utc))
    return User(**{**data, **kwargs})


def test_user_creation() -> None:
    user = make_user()
    assert user.is_blocked is False
    assert user.role == UserRoles.BUYER


def test_user_invalid_email() -> None:
    with pytest.raises(ValidationError):
        make_user(email='not-an-email')


def test_user_name_required() -> None:
    with pytest.raises(ValidationError):
        make_user(name='')


def test_user_role_required() -> None:
    with pytest.raises(ValidationError):
        User(id=uuid4(), email='a@b.ru', name='a', created_at=datetime.now(timezone.utc))


def test_user_assignment_is_validated() -> None:
    user = make_user()
    with pytest.raises(ValidationError):
        user.is_blocked = 'maybe'


def test_register_request_default_role() -> None:
    request = RegisterUserRequest.model_validate({'email': 'a@b.ru', 'name': 'Анна'})
    assert request.role == UserRoles.BUYER


def test_register_request_parses_role() -> None:
    request = RegisterUserRequest.model_validate({'email': 'a@b.ru', 'name': 'Анна', 'role': 'seller'})
    assert request.role == UserRoles.SELLER
