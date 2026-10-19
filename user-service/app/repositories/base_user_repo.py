from abc import ABC, abstractmethod
from uuid import UUID

from app.models.user import User, UserRoles


class BaseUserRepo(ABC):
    @abstractmethod
    def get_users(self, role: UserRoles | None = None, offset: int = 0,
                  count: int | None = None) -> list[User]:
        """Список пользователей, отсортированный по дате регистрации."""

    @abstractmethod
    def get_user(self, user_id: UUID) -> User:
        """KeyError, если пользователя нет."""

    @abstractmethod
    def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def create_user(self, user: User) -> User:
        """KeyError, если пользователь с таким id уже есть."""

    @abstractmethod
    def save_user(self, user: User) -> User:
        """KeyError, если пользователя нет."""
