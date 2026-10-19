from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_user_service
from app.models.user import User, UserRoles, RegisterUserRequest
from app.services.user_service import UserService

user_router = APIRouter(prefix='/users', tags=['Users'])


@user_router.post('', status_code=201)
def register(body: RegisterUserRequest, service: UserService = Depends(get_user_service)) -> User:
    try:
        return service.register(body.email, body.name, body.role)
    except ValueError as e:
        raise HTTPException(409, str(e))


@user_router.get('')
def get_users(role: UserRoles | None = None,
              offset: int = Query(0, ge=0),
              count: int = Query(20, ge=1, le=100),
              service: UserService = Depends(get_user_service)) -> list[User]:
    return service.get_users(role, offset, count)


@user_router.get('/{user_id}')
def get_user(user_id: UUID, service: UserService = Depends(get_user_service)) -> User:
    try:
        return service.get_user(user_id)
    except KeyError:
        raise HTTPException(404, f'User with id={user_id} not found')


@user_router.post('/{user_id}:block')
def block_user(user_id: UUID, service: UserService = Depends(get_user_service)) -> User:
    try:
        return service.block_user(user_id)
    except KeyError:
        raise HTTPException(404, f'User with id={user_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))
