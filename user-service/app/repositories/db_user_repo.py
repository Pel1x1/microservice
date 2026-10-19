from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRoles
from app.repositories.base_user_repo import BaseUserRepo
from app.schemas.user import User as DBUser


class DbUserRepo(BaseUserRepo):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_users(self, role: UserRoles | None = None, offset: int = 0,
                  count: int | None = None) -> list[User]:
        query = select(DBUser).order_by(DBUser.created_at)
        if role is not None:
            query = query.where(DBUser.role == role)
        query = query.offset(offset)
        if count is not None:
            query = query.limit(count)
        return [User.model_validate(u) for u in self.db.scalars(query).all()]

    def get_user(self, user_id: UUID) -> User:
        user = self.db.get(DBUser, user_id)
        if user is None:
            raise KeyError(user_id)
        return User.model_validate(user)

    def find_by_email(self, email: str) -> User | None:
        user = self.db.scalars(select(DBUser).where(DBUser.email == email)).first()
        return None if user is None else User.model_validate(user)

    def create_user(self, user: User) -> User:
        if self.db.get(DBUser, user.id) is not None:
            raise KeyError(user.id)
        self.db.add(DBUser(**user.model_dump()))
        self.db.commit()
        return user

    def save_user(self, user: User) -> User:
        db_user = self.db.get(DBUser, user.id)
        if db_user is None:
            raise KeyError(user.id)
        db_user.name = user.name
        db_user.is_blocked = user.is_blocked
        self.db.commit()
        return user
