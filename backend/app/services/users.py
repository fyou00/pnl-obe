"""Admin-scoped user account CRUD, activation, and password reset services."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Angkatan, AuditLog, Mahasiswa, User
from app.schemas.auth import Role
from app.schemas.users import (
    AdminResetPasswordRequest,
    UserCreate,
    UserManageResponse,
    UserUpdate,
)
from app.services.auth import safe_user_snapshot
from app.services.curriculum import conflict, owned, search, transaction


def _to_response(row: User, angkatan: Angkatan | None) -> UserManageResponse:
    return UserManageResponse(
        id=row.id,
        prodi_id=row.prodi_id,
        nim_nidn=row.nim_nidn,
        nama=row.nama,
        email=row.email,
        role=row.role,
        aktif=row.aktif,
        angkatan_id=angkatan.id if angkatan else None,
        tahun_masuk=angkatan.tahun_masuk if angkatan else None,
    )


def _load_response(db: Session, row: User) -> UserManageResponse:
    angkatan = db.scalar(
        select(Angkatan)
        .join(Mahasiswa, Mahasiswa.angkatan_id == Angkatan.id)
        .where(Mahasiswa.id == row.id)
    )
    return _to_response(row, angkatan)


def list_users(
    db: Session,
    admin: User,
    *,
    offset: int = 0,
    limit: int = 50,
    role: Role | None = None,
    aktif: bool | None = None,
    angkatan_id: UUID | None = None,
    q: str | None = None,
) -> list[UserManageResponse]:
    query = (
        select(User, Angkatan)
        .outerjoin(Mahasiswa, Mahasiswa.id == User.id)
        .outerjoin(Angkatan, Angkatan.id == Mahasiswa.angkatan_id)
        .where(User.prodi_id == admin.prodi_id)
    )
    if role is not None:
        query = query.where(User.role == role)
    if aktif is not None:
        query = query.where(User.aktif == aktif)
    if angkatan_id is not None:
        query = query.where(Mahasiswa.angkatan_id == angkatan_id)
    query = search(query, [User.nama, User.email, User.nim_nidn], q)
    rows = db.execute(
        query.order_by(User.role, User.nama, User.nim_nidn, User.id).offset(offset).limit(limit)
    ).all()
    return [_to_response(user_row, angkatan_row) for user_row, angkatan_row in rows]


def get_user(db: Session, admin: User, user_id: UUID) -> UserManageResponse:
    row = owned(db, User, user_id, admin)
    return _load_response(db, row)


def create_user(db: Session, admin: User, payload: UserCreate) -> UserManageResponse:
    with transaction(db):
        if db.scalar(select(User.id).where(func.lower(User.email) == payload.email).limit(1)):
            conflict("Email sudah digunakan")
        if db.scalar(select(User.id).where(User.nim_nidn == payload.nim_nidn).limit(1)):
            conflict("NIM/NIDN sudah digunakan")
        if payload.angkatan_id is not None:
            owned(db, Angkatan, payload.angkatan_id, admin, lock=True)

        row = User(
            prodi_id=admin.prodi_id,
            nim_nidn=payload.nim_nidn,
            nama=payload.nama,
            email=payload.email,
            role=payload.role,
            password_hash=hash_password(payload.password),
            aktif=payload.aktif,
        )
        db.add(row)
        db.flush()
        if payload.role == "Mahasiswa" and payload.angkatan_id is not None:
            db.add(Mahasiswa(id=row.id, angkatan_id=payload.angkatan_id))
        db.flush()
        db.add(
            AuditLog(
                aktor_id=admin.id,
                aksi="create",
                entitas="users",
                entitas_id=row.id,
                sebelum=None,
                sesudah=safe_user_snapshot(row, angkatan_id=payload.angkatan_id),
            )
        )
    return _load_response(db, row)


def update_user(db: Session, admin: User, user_id: UUID, payload: UserUpdate) -> UserManageResponse:
    with transaction(db):
        row = owned(db, User, user_id, admin, lock=True)
        if row.id == admin.id and payload.aktif is False:
            conflict("Akun Admin sendiri tidak dapat dinonaktifkan")
        if row.role == "Admin" and row.id != admin.id:
            conflict("Akun Admin lain tidak dapat diubah melalui modul ini")

        changes = payload.model_dump(exclude_unset=True)
        mhs = db.get(Mahasiswa, row.id)
        before = safe_user_snapshot(row, angkatan_id=mhs.angkatan_id if mhs else None)

        if "email" in changes and db.scalar(
            select(User.id)
            .where(func.lower(User.email) == changes["email"], User.id != row.id)
            .limit(1)
        ):
            conflict("Email sudah digunakan")
        if "nim_nidn" in changes and db.scalar(
            select(User.id).where(User.nim_nidn == changes["nim_nidn"], User.id != row.id).limit(1)
        ):
            conflict("NIM/NIDN sudah digunakan")

        if "angkatan_id" in changes:
            target_angkatan_id = changes.pop("angkatan_id")
            if row.role != "Mahasiswa":
                conflict("angkatan_id hanya berlaku untuk peran Mahasiswa")
            if mhs is not None:
                if mhs.angkatan_id != target_angkatan_id:
                    conflict("Mahasiswa sudah terdaftar pada angkatan")
            else:
                owned(db, Angkatan, target_angkatan_id, admin, lock=True)
                mhs = Mahasiswa(id=row.id, angkatan_id=target_angkatan_id)
                db.add(mhs)

        was_aktif = row.aktif
        for key, value in changes.items():
            setattr(row, key, value)
        if was_aktif and not row.aktif:
            row.token_version += 1

        db.flush()
        db.add(
            AuditLog(
                aktor_id=admin.id,
                aksi="update",
                entitas="users",
                entitas_id=row.id,
                sebelum=before,
                sesudah=safe_user_snapshot(row, angkatan_id=mhs.angkatan_id if mhs else None),
            )
        )
    return _load_response(db, row)


def reset_user_password(
    db: Session, admin: User, user_id: UUID, payload: AdminResetPasswordRequest
) -> UserManageResponse:
    with transaction(db):
        row = owned(db, User, user_id, admin, lock=True)
        if row.id == admin.id:
            conflict("Gunakan fitur ganti kata sandi untuk mengubah kata sandi akun sendiri")
        if row.role == "Admin":
            conflict("Kata sandi akun Admin lain tidak dapat direset melalui modul ini")

        row.password_hash = hash_password(payload.password_baru)
        row.token_version += 1
        mhs = db.get(Mahasiswa, row.id)
        db.flush()
        db.add(
            AuditLog(
                aktor_id=admin.id,
                aksi="reset_password",
                entitas="users",
                entitas_id=row.id,
                alasan=payload.alasan or "Reset kata sandi oleh Admin",
                sebelum=None,
                sesudah=safe_user_snapshot(row, angkatan_id=mhs.angkatan_id if mhs else None),
            )
        )
    return _load_response(db, row)
