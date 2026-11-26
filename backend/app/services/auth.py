import secrets
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import AuditLog, Prodi, User
from app.services.curriculum import transaction

# Used only to equalize bcrypt work for unknown accounts; never an account credential.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


def safe_user_snapshot(row: User, *, angkatan_id: UUID | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(row.id),
        "prodi_id": str(row.prodi_id),
        "nim_nidn": row.nim_nidn,
        "nama": row.nama,
        "email": row.email,
        "role": row.role,
        "aktif": row.aktif,
    }
    if angkatan_id is not None:
        data["angkatan_id"] = str(angkatan_id)
    return data


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid or not user.aktif:
        return None
    prodi = db.get(Prodi, user.prodi_id)
    if prodi is None or not prodi.aktif:
        return None
    return user


def revoke_all_tokens(db: Session, user: User) -> None:
    # Atomic increment also invalidates tokens issued by other browser sessions.
    db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    db.commit()


def change_password(db: Session, user: User, password_lama: str, password_baru: str) -> User:
    with transaction(db):
        row = db.scalar(
            select(User)
            .where(User.id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None or not verify_password(password_lama, row.password_hash):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kata sandi saat ini tidak sesuai")
        row.password_hash = hash_password(password_baru)
        row.token_version += 1
        db.flush()
        db.add(
            AuditLog(
                aktor_id=row.id,
                aksi="change_password",
                entitas="users",
                entitas_id=row.id,
                sebelum=None,
                sesudah=safe_user_snapshot(row),
            )
        )
    db.refresh(row)
    return row
