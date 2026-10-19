# /tests/integration/test_user_repo_db.py
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User, UserRoles
from app.repositories.db_user_repo import DbUserRepo
from app.services.user_service import UserService


@pytest.fixture()
def repo(db: Session) -> DbUserRepo:
    return DbUserRepo(db)


def new_user(email: str = 'a@example.com', role: UserRoles = UserRoles.BUYER, minutes: int = 0) -> User:
    return User(id=uuid4(), email=email, name='Имя', role=role,
                created_at=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))


def test_empty_list(repo: DbUserRepo) -> None:
    assert repo.get_users() == []


def test_create_and_get(repo: DbUserRepo) -> None:
    user = new_user()
    assert repo.create_user(user) == user
    assert repo.get_user(user.id) == user


def test_create_repeat(repo: DbUserRepo) -> None:
    user = new_user()
    repo.create_user(user)
    with pytest.raises(KeyError):
        repo.create_user(user)


def test_email_is_unique(repo: DbUserRepo, db: Session) -> None:
    repo.create_user(new_user('same@example.com'))
    with pytest.raises(IntegrityError):
        repo.create_user(new_user('same@example.com'))
    db.rollback()


def test_get_not_found(repo: DbUserRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_user(uuid4())


def test_find_by_email(repo: DbUserRepo) -> None:
    user = new_user('find@example.com')
    repo.create_user(user)
    assert repo.find_by_email('find@example.com') == user
    assert repo.find_by_email('none@example.com') is None


def test_save_user(repo: DbUserRepo) -> None:
    user = new_user()
    repo.create_user(user)
    user.is_blocked = True
    repo.save_user(user)
    assert repo.get_user(user.id).is_blocked is True


def test_save_unknown_user(repo: DbUserRepo) -> None:
    with pytest.raises(KeyError):
        repo.save_user(new_user())


def test_filters_sorting_pagination(repo: DbUserRepo) -> None:
    third, first, second = new_user('3@e.com', minutes=30), new_user('1@e.com', minutes=10), \
        new_user('2@e.com', UserRoles.SELLER, minutes=20)
    for user in (third, first, second):
        repo.create_user(user)
    assert [u.id for u in repo.get_users()] == [first.id, second.id, third.id]
    assert [u.id for u in repo.get_users(offset=1, count=1)] == [second.id]
    assert [u.id for u in repo.get_users(UserRoles.SELLER)] == [second.id]


def test_service_register_and_block_with_db(repo: DbUserRepo) -> None:
    """Бизнес-логика поверх настоящей БД."""
    service = UserService(repo)
    user = service.register('db@example.com', 'DB')
    service.block_user(user.id)
    assert repo.get_user(user.id).is_blocked is True
