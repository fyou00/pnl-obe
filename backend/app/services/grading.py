"""Atomic grade writes and period transitions share the period/design lock order."""

from datetime import UTC, datetime

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.models import (
    Angkatan,
    AuditLog,
    Mahasiswa,
    MahasiswaPeriode,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    User,
)
from app.services import academic, assessment
from app.services.access import require_class_access
from app.services.curriculum import conflict, owned, snapshot, transaction


def list_grades(db, user, class_id):
    require_class_access(db, user, class_id)
    query = select(NilaiMahasiswa).where(NilaiMahasiswa.kelas_mk_id == class_id)
    if user.role == "Mahasiswa":
        query = query.where(NilaiMahasiswa.mahasiswa_id == user.id)
    return list(
        db.scalars(query.order_by(NilaiMahasiswa.mahasiswa_id, NilaiMahasiswa.instrumen_id))
    )


def save_grades(db, user, class_id, payload):
    if user.role != "Dosen":
        raise HTTPException(403, "Hanya Dosen pengampu yang dapat menginput nilai")
    with transaction(db):
        initial = require_class_access(db, user, class_id)
        academic.period(db, user, initial[2].id, edit=True)
        # Refresh after waiting: assignment/roster may have changed before the lock.
        context = require_class_access(db, user, class_id)
        course, klass, periode, mk, _, design, _ = context
        design = assessment.design(db, user, design.id, lock=True)
        if design.periode_id != periode.id or design.kurikulum_mk_id != mk.id:
            conflict("Konteks kelas dan rancangan tidak sesuai")
        if not assessment.summary(db, user, design).siap_dinilai:
            conflict("Rancangan belum siap dinilai: lengkapi pemetaan dan bobot 100%")
        instruments = {i.id for i in db.scalars(assessment.instrument_query(design.id))}
        requested = {item.mahasiswa_id for item in payload.items}
        participants = set(
            db.scalars(
                select(PesertaKelasMK.mahasiswa_id)
                .join(User, PesertaKelasMK.mahasiswa_id == User.id)
                .join(Mahasiswa, Mahasiswa.id == User.id)
                .join(Angkatan, Angkatan.id == Mahasiswa.angkatan_id)
                .join(MahasiswaPeriode, MahasiswaPeriode.mahasiswa_id == User.id)
                .where(
                    PesertaKelasMK.kelas_mk_id == course.id,
                    PesertaKelasMK.mk_id == mk.mk_id,
                    User.id.in_(requested),
                    User.role == "Mahasiswa",
                    User.aktif.is_(True),
                    User.prodi_id == user.prodi_id,
                    Mahasiswa.angkatan_id == klass.angkatan_id,
                    Angkatan.prodi_id == user.prodi_id,
                    Angkatan.kurikulum_id == mk.kurikulum_id,
                    MahasiswaPeriode.periode_id == periode.id,
                    MahasiswaPeriode.kelas_periode_id == klass.id,
                    MahasiswaPeriode.status == "Aktif",
                )
            )
        )
        if requested - participants or any(
            i.instrumen_id not in instruments for i in payload.items
        ):
            raise HTTPException(404, "Instrumen atau peserta aktif tidak ditemukan pada kelas ini")
        existing = {
            (g.instrumen_id, g.mahasiswa_id): g
            for g in db.scalars(
                select(NilaiMahasiswa).where(
                    NilaiMahasiswa.kelas_mk_id == class_id,
                    NilaiMahasiswa.mahasiswa_id.in_(requested),
                )
            )
        }
        result = []
        for item in payload.items:
            row = existing.get((item.instrumen_id, item.mahasiswa_id))
            if row is not None and row.nilai_mentah == item.nilai_mentah:
                result.append(row)
                continue
            before = assessment.row_snapshot(row) if row else None
            action = "update" if row else "create"
            if row is None:
                row = NilaiMahasiswa(kelas_mk_id=class_id, **item.model_dump(), diubah_oleh=user.id)
                db.add(row)
            else:
                row.nilai_mentah = item.nilai_mentah
                row.diubah_oleh = user.id
                row.waktu_input = datetime.now(UTC)
            db.flush()
            academic.record(
                db,
                user,
                action,
                row,
                before,
                periode_id=periode.id,
                after=assessment.row_snapshot(row),
            )
            result.append(row)
    return result


def transition_period(db, user, period_id, *, reopen=False, reason=None):
    if user.role != "Admin":
        raise HTTPException(403, "Hanya Admin yang dapat mengubah status periode")
    if reopen and (not reason or not reason.strip()):
        raise HTTPException(422, "Alasan pembukaan kembali wajib diisi")
    with transaction(db):
        row = owned(db, PeriodeAkademik, period_id, user, lock=True)
        expected = "Ditutup" if reopen else "Dibuka"
        if row.status != expected:
            conflict("Status periode tidak sesuai untuk transisi ini")
        before = snapshot(row)
        row.status = "Dibuka" if reopen else "Ditutup"
        row.ditutup_pada = None if reopen else datetime.now(UTC)
        row.ditutup_oleh = None if reopen else user.id
        db.add(
            AuditLog(
                aktor_id=user.id,
                periode_id=row.id,
                aksi="reopen" if reopen else "close",
                entitas=row.__tablename__,
                entitas_id=row.id,
                alasan=reason.strip() if reopen else None,
                sebelum=jsonable_encoder(before),
                sesudah=jsonable_encoder(snapshot(row)),
            )
        )
    return row
