from uuid import UUID

from app.models.user import User, UserRoles
from app.repositories.base_user_repo import BaseUserRepo


class LocalUserRepo(BaseUserRepo):
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    def get_users(self, role: UserRoles | None = None, offset: int = 0,
                  count: int | None = None) -> list[User]:
        users = sorted(self._users.values(), key=lambda u: u.created_at)
        users = [u.model_copy() for u in users if role is None or u.role == role]
        end = None if count is None else offset + count
        return users[offset:end]

    def get_user(self, user_id: UUID) -> User:
        if user_id not in self._users:
            raise KeyError(user_id)
        return self._users[user_id].model_copy()

    def find_by_email(self, email: str) -> User | None:
        return next((u.model_copy() for u in self._users.values() if u.email == email), None)

    def create_user(self, user: User) -> User:
        if user.id in self._users:
            raise KeyError(user.id)
        self._users[user.id] = user.model_copy()
        return user

    def save_user(self, user: User) -> User:
        if user.id not in self._users:
            raise KeyError(user.id)
        self._users[user.id] = user.model_copy()
        return user
