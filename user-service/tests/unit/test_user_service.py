# /tests/unit/test_user_service.py
from uuid import uuid4

import pytest

from app.models.user import UserRoles
from app.repositories.local_user_repo import LocalUserRepo
from app.services.user_service import UserService
from tests.unit.fakes import FakePublisher


@pytest.fixture()
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture()
def service(publisher: FakePublisher) -> UserService:
    # Dependency injection: локальный репозиторий и мок брокера
    return UserService(LocalUserRepo(), publisher)


def test_empty_users(service: UserService) -> None:
    assert service.get_users() == []


def test_register(service: UserService, publisher: FakePublisher) -> None:
    user = service.register('Ivan@Example.com ', 'Иван')
    assert user.email == 'ivan@example.com'          # email нормализуется
    assert user.role == UserRoles.BUYER
    assert service.get_user(user.id) == user
    assert publisher.events == [('user.registered', {'user_id': str(user.id), 'role': 'buyer'})]


def test_register_seller(service: UserService) -> None:
    assert service.register('shop@example.com', 'Магазин', UserRoles.SELLER).role == UserRoles.SELLER


def test_register_duplicate_email(service: UserService) -> None:
    service.register('a@example.com', 'A')
    with pytest.raises(ValueError):
        service.register('A@EXAMPLE.COM', 'B')


def test_register_admin_forbidden(service: UserService, publisher: FakePublisher) -> None:
    with pytest.raises(ValueError):
        service.register('root@example.com', 'Root', UserRoles.ADMIN)
    assert publisher.events == []


def test_get_user_not_found(service: UserService) -> None:
    with pytest.raises(KeyError):
        service.get_user(uuid4())


def test_block_user(service: UserService, publisher: FakePublisher) -> None:
    user = service.register('a@example.com', 'A')
    blocked = service.block_user(user.id)
    assert blocked.is_blocked is True
    assert service.get_user(user.id).is_blocked is True
    assert publisher.events[-1] == ('user.blocked', {'user_id': str(user.id)})


def test_block_twice_forbidden(service: UserService) -> None:
    user = service.register('a@example.com', 'A')
    service.block_user(user.id)
    with pytest.raises(ValueError):
        service.block_user(user.id)


def test_block_unknown_user(service: UserService) -> None:
    with pytest.raises(KeyError):
        service.block_user(uuid4())


def test_filter_by_role_and_pagination(service: UserService) -> None:
    buyers = [service.register(f'b{i}@example.com', f'B{i}') for i in range(3)]
    seller = service.register('s@example.com', 'S', UserRoles.SELLER)
    assert len(service.get_users()) == 4
    assert [u.id for u in service.get_users(UserRoles.SELLER)] == [seller.id]
    assert [u.id for u in service.get_users(UserRoles.BUYER, offset=1, count=1)] == [buyers[1].id]
