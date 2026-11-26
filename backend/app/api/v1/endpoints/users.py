"""Admin user management endpoints (scoped by admin prodi)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DB, require_roles
from app.models import User
from app.schemas.auth import Role
from app.schemas.users import (
    AdminResetPasswordRequest,
    UserCreate,
    UserManageResponse,
    UserUpdate,
)
from app.services import users as service

Admin = Annotated[User, Depends(require_roles("Admin"))]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=100)]
router = APIRouter(prefix="/pengguna", tags=["admin-pengguna"])


@router.get("", response_model=list[UserManageResponse])
def list_users(
    db: DB,
    user: Admin,
    offset: Offset = 0,
    limit: Limit = 50,
    role: Role | None = None,
    aktif: bool | None = None,
    angkatan_id: UUID | None = None,
    q: Search = None,
):
    return service.list_users(
        db,
        user,
        offset=offset,
        limit=limit,
        role=role,
        aktif=aktif,
        angkatan_id=angkatan_id,
        q=q,
    )


@router.post("", response_model=UserManageResponse, status_code=201)
def create_user(db: DB, user: Admin, payload: UserCreate):
    return service.create_user(db, user, payload)


@router.get("/{user_id}", response_model=UserManageResponse)
def get_user(db: DB, user: Admin, user_id: UUID):
    return service.get_user(db, user, user_id)


@router.patch("/{user_id}", response_model=UserManageResponse)
def update_user(db: DB, user: Admin, user_id: UUID, payload: UserUpdate):
    return service.update_user(db, user, user_id, payload)


@router.post("/{user_id}/reset-password", response_model=UserManageResponse)
def reset_user_password(db: DB, user: Admin, user_id: UUID, payload: AdminResetPasswordRequest):
    return service.reset_user_password(db, user, user_id, payload)
