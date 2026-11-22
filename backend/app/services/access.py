"""Centralized class-level RBAC for current and future academic routes."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    KelasMK,
    KelasPeriode,
    KurikulumMK,
    MataKuliah,
    PeriodeAkademik,
    PesertaKelasMK,
    Prodi,
    RancanganPenilaian,
    User,
)


def accessible_classes(user: User):
    query = (
        select(
            KelasMK,
            KelasPeriode,
            PeriodeAkademik,
            KurikulumMK,
            MataKuliah,
            RancanganPenilaian,
            Prodi,
        )
        .join(KelasPeriode, KelasMK.kelas_periode_id == KelasPeriode.id)
        .join(PeriodeAkademik, KelasPeriode.periode_id == PeriodeAkademik.id)
        .join(KurikulumMK, KelasMK.kurikulum_mk_id == KurikulumMK.id)
        .join(MataKuliah, KurikulumMK.mk_id == MataKuliah.id)
        .join(RancanganPenilaian, KelasMK.rancangan_id == RancanganPenilaian.id)
        .join(Prodi, PeriodeAkademik.prodi_id == Prodi.id)
        .where(PeriodeAkademik.prodi_id == user.prodi_id)
    )
    if user.role == "Dosen":
        query = query.where(RancanganPenilaian.dosen_id == user.id)
    elif user.role == "Mahasiswa":
        query = query.join(PesertaKelasMK, PesertaKelasMK.kelas_mk_id == KelasMK.id).where(
            PesertaKelasMK.mahasiswa_id == user.id
        )
    elif user.role != "Admin":
        raise HTTPException(403, "Peran tidak memiliki akses")
    return query


def require_class_access(db: Session, user: User, kelas_mk_id: UUID):
    row = db.execute(
        accessible_classes(user)
        .where(KelasMK.id == kelas_mk_id)
        .execution_options(populate_existing=True)
    ).first()
    if row is None:
        # Same response for missing and out-of-scope IDs; avoids leaking other classes.
        raise HTTPException(404, "Kelas mata kuliah tidak ditemukan")
    return row
