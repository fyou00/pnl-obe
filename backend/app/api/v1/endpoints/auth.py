from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import DB, CurrentUser, unauthorized
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import TokenResponse, UserResponse
from app.services.auth import authenticate, revoke_all_tokens

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def login(
    request: Request, db: DB, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> TokenResponse:
    """OAuth2 form: username berisi email institusi. Tidak ada registrasi publik."""
    user = authenticate(db, form.username, form.password)
    if user is None:
        raise unauthorized()
    settings = request.app.state.settings
    return TokenResponse(
        access_token=create_access_token(user, settings),
        expires_in=settings.access_token_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user


@router.post("/logout", status_code=204)
def logout(db: DB, user: CurrentUser) -> Response:
    """Cabut seluruh access token pengguna ini, termasuk sesi browser lain."""
    revoke_all_tokens(db, user)
    return Response(status_code=204)
