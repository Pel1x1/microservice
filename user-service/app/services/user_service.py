from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.models.user import User, UserRoles
from app.repositories.base_user_repo import BaseUserRepo
from app.clients.publisher import EventPublisher


class UserService:
    """Бизнес-логика контекста «Управление пользователями».

    KeyError   — пользователь не найден;
    ValueError — нарушено бизнес-правило.
    """

    def __init__(self, user_repo: BaseUserRepo, publisher: EventPublisher | None = None) -> None:
        self.user_repo = user_repo
        self.publisher = publisher

    def get_users(self, role: UserRoles | None = None, offset: int = 0,
                  count: int | None = None) -> list[User]:
        return self.user_repo.get_users(role, offset, count)

    def get_user(self, user_id: UUID) -> User:
        return self.user_repo.get_user(user_id)

    def register(self, email: str, name: str, role: UserRoles = UserRoles.BUYER) -> User:
        """Команда «Зарегистрироваться» (покупатель/продавец)."""
        if role == UserRoles.ADMIN:
            raise ValueError('Администратор не может зарегистрироваться самостоятельно')
        email = email.strip().lower()
        if self.user_repo.find_by_email(email) is not None:
            raise ValueError(f'Пользователь с email {email} уже зарегистрирован')
        user = User(id=uuid4(), email=email, name=name, role=role,
                    created_at=datetime.now(timezone.utc))
        self.user_repo.create_user(user)
        self._publish('user.registered', {'user_id': str(user.id), 'role': user.role.value})
        return user

    def block_user(self, user_id: UUID) -> User:
        """Команда «Заблокировать пользователя» (администратор)."""
        user = self.user_repo.get_user(user_id)
        if user.is_blocked:
            raise ValueError('Пользователь уже заблокирован')
        if user.role == UserRoles.ADMIN:
            raise ValueError('Администратора заблокировать нельзя')
        user.is_blocked = True
        self.user_repo.save_user(user)
        self._publish('user.blocked', {'user_id': str(user.id)})
        return user

    def _publish(self, routing_key: str, payload: dict) -> None:
        if self.publisher is not None:
            self.publisher.publish(routing_key, payload)
