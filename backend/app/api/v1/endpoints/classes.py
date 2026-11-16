from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.dependencies import DB, CurrentUser, require_roles
from app.models import KelasMK, KelasPeriode, PesertaKelasMK, User
from app.schemas.academic import KelasMKResponse
from app.services.access import accessible_classes, require_class_access

router = APIRouter(prefix="/kelas-mk", tags=["kelas-mk"])


def serialize_class(row) -> KelasMKResponse:
    kelas_mk, kelas, periode, mk, master, rancangan, prodi = row
    return KelasMKResponse(
        id=kelas_mk.id,
        periode_id=periode.id,
        tahun_akademik=periode.tahun_akademik,
        semester=periode.semester,
        kelas=f"{prodi.kode_prodi}-{kelas.tingkat}{kelas.kode_kelas}",
        kurikulum_mk_id=mk.id,
        kode_mk=master.kode_mk,
        nama_mk=mk.nama_mk,
        dosen_id=rancangan.dosen_id,
        rancangan_id=rancangan.id,
    )


@router.get("", response_model=list[KelasMKResponse])
def list_classes(
    db: DB,
    user: CurrentUser,
    periode_id: UUID,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    rows = db.execute(
        accessible_classes(user)
        .where(KelasPeriode.periode_id == periode_id)
        .order_by(KelasMK.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [serialize_class(row) for row in rows]


@router.get("/{kelas_mk_id}", response_model=KelasMKResponse)
def class_detail(db: DB, user: CurrentUser, kelas_mk_id: UUID):
    return serialize_class(require_class_access(db, user, kelas_mk_id))


@router.get("/{kelas_mk_id}/peserta", response_model=list[UUID])
def class_participants(
    db: DB, kelas_mk_id: UUID, user: Annotated[User, Depends(require_roles("Admin", "Dosen"))]
):
    require_class_access(db, user, kelas_mk_id)
    return list(
        db.scalars(
            select(PesertaKelasMK.mahasiswa_id).where(PesertaKelasMK.kelas_mk_id == kelas_mk_id)
        )
    )
