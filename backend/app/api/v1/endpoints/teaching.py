from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DB, require_roles
from app.models import User
from app.schemas.teaching import (
    ApplyPackage,
    AssignmentResponse,
    LecturerPatch,
    LecturerResponse,
    PackagePreview,
    PackageResult,
)
from app.services import teaching as service

Admin = Annotated[User, Depends(require_roles("Admin"))]
router = APIRouter(tags=["admin-paket-pengampu"])


@router.get("/dosen", response_model=list[LecturerResponse])
def lecturers(
    db: DB,
    user: Admin,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    q: Annotated[str | None, Query(max_length=100)] = None,
    aktif: bool | None = True,
):
    return service.list_lecturers(db, user, offset, limit, q, aktif)


@router.get(
    "/periode-akademik/{periode_id}/angkatan/{angkatan_id}/paket", response_model=PackagePreview
)
def preview(db: DB, user: Admin, periode_id: UUID, angkatan_id: UUID):
    return service.preview(db, user, periode_id, angkatan_id)


@router.post(
    "/periode-akademik/{periode_id}/angkatan/{angkatan_id}/paket/terapkan",
    response_model=PackageResult,
)
def apply(db: DB, user: Admin, periode_id: UUID, angkatan_id: UUID, payload: ApplyPackage):
    return service.apply(db, user, periode_id, angkatan_id, payload)


@router.patch("/kelas-mk/{kelas_mk_id}/pengampu", response_model=AssignmentResponse)
def change_lecturer(db: DB, user: Admin, kelas_mk_id: UUID, payload: LecturerPatch):
    return service.change_lecturer(db, user, kelas_mk_id, payload)
