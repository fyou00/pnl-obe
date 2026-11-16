from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.models import Prodi, User
from app.schemas.auth import Role

bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.database.session_factory() as session:
        yield session


DB = Annotated[Session, Depends(get_db)]


def unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Token atau kredensial tidak valid",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(request: Request, db: DB, token: Annotated[str, Depends(bearer)]) -> User:
    try:
        claims = decode_access_token(token, request.app.state.settings)
        user_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None or not user.aktif or user.token_version != claims["ver"]:
        raise unauthorized()
    prodi = db.get(Prodi, user.prodi_id)
    if prodi is None or not prodi.aktif:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Peran tidak memiliki akses")
        return user

    return dependency
