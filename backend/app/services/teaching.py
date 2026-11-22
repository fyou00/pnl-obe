"""Atomic, repeatable campus package application and one-lecturer assignments."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    MKCPL,
    Angkatan,
    KelasMK,
    KelasPeriode,
    Kurikulum,
    KurikulumMK,
    Mahasiswa,
    MahasiswaPeriode,
    MasterCPL,
    MataKuliah,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    RancanganPenilaian,
    User,
)
from app.schemas.teaching import AssignmentResponse, PackagePreview, PackageResult
from app.services import academic
from app.services.access import require_class_access
from app.services.curriculum import conflict, owned, search, snapshot, transaction


@dataclass
class PackageContext:
    cohort: Angkatan
    periode: PeriodeAkademik
    kurikulum: Kurikulum
    classes: list[KelasPeriode]
    courses: list[KurikulumMK]
    masters: dict[UUID, MataKuliah]
    semester: int


def context(db, user, periode_id, angkatan_id, *, edit=False):
    # Same order as roster corrections: cohort -> period -> users/designs.
    cohort = owned(db, Angkatan, angkatan_id, user, lock=edit)
    periode = academic.period(db, user, periode_id, edit=edit)
    kurikulum = owned(db, Kurikulum, cohort.kurikulum_id, user)
    if kurikulum.status not in ("Aktif", "Arsip"):
        conflict("Paket memerlukan kurikulum Aktif atau Arsip yang telah ditetapkan ke angkatan")
    classes = list(
        db.scalars(
            select(KelasPeriode)
            .where(
                KelasPeriode.periode_id == periode.id,
                KelasPeriode.angkatan_id == cohort.id,
                KelasPeriode.kode_kelas != "K",
            )
            .order_by(KelasPeriode.kode_kelas, KelasPeriode.id)
        )
    )
    if not classes:
        conflict("Angkatan belum mempunyai kelas reguler pada periode ini")
    for klass in classes:
        academic.validate_class(
            db, user, cohort, periode, klass.kode_kelas, klass.semester_studi, klass.id
        )
    semester = classes[0].semester_studi
    courses = list(
        db.scalars(
            select(KurikulumMK)
            .where(KurikulumMK.kurikulum_id == kurikulum.id, KurikulumMK.semester == semester)
            .order_by(KurikulumMK.id)
        )
    )
    if not courses:
        conflict("Paket MK untuk semester studi ini belum tersedia")
    masters = {}
    for course in courses:
        masters[course.id] = owned(db, MataKuliah, course.mk_id, user)
        links = list(db.scalars(select(MKCPL).where(MKCPL.kurikulum_mk_id == course.id)))
        if not links:
            conflict("Setiap MK paket wajib mempunyai pembebanan CPL")
        for link in links:
            cpl = db.get(MasterCPL, link.cpl_id)
            if cpl.kurikulum_id != kurikulum.id or (
                cpl.prodi_id is not None and cpl.prodi_id != user.prodi_id
            ):
                conflict("CPL paket berasal dari versi/prodi yang tidak sesuai")
    return PackageContext(cohort, periode, kurikulum, classes, courses, masters, semester)


def lecturers(db, user, ids, *, lock=False):
    query = (
        select(User)
        .where(
            User.id.in_(ids),
            User.prodi_id == user.prodi_id,
            User.role == "Dosen",
            User.aktif.is_(True),
        )
        .order_by(User.id)
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    rows = {row.id: row for row in db.scalars(query)}
    if set(rows) != set(ids):
        # Distinguish invalid role/status in own prodi from missing/out-of-scope IDs.
        for entity_id in set(ids) - set(rows):
            account = owned(db, User, entity_id, user)
            if account.role != "Dosen" or not account.aktif:
                conflict("Pengampu harus akun Dosen aktif pada prodi yang sama")
    return rows


def list_lecturers(db, user, offset, limit, q, aktif):
    query = select(User).where(User.prodi_id == user.prodi_id, User.role == "Dosen")
    if aktif is not None:
        query = query.where(User.aktif == aktif)
    query = search(query, [User.nim_nidn, User.nama], q)
    return list(db.scalars(query.order_by(User.nama, User.id).offset(offset).limit(limit)))


def active_roster(db, user, ctx, *, lock=False):
    all_class_ids = select(KelasPeriode.id).where(
        KelasPeriode.periode_id == ctx.periode.id, KelasPeriode.angkatan_id == ctx.cohort.id
    )
    rows = db.execute(
        select(MahasiswaPeriode, Mahasiswa)
        .join(Mahasiswa, Mahasiswa.id == MahasiswaPeriode.mahasiswa_id)
        .where(
            MahasiswaPeriode.periode_id == ctx.periode.id,
            or_(
                Mahasiswa.angkatan_id == ctx.cohort.id,
                MahasiswaPeriode.kelas_periode_id.in_(all_class_ids),
            ),
        )
        .order_by(MahasiswaPeriode.mahasiswa_id)
    ).all()
    active_ids = {row.mahasiswa_id for row, profile in rows if row.status == "Aktif"}
    accounts_query = (
        select(User)
        .where(
            User.id.in_(active_ids),
            User.prodi_id == user.prodi_id,
            User.role == "Mahasiswa",
            User.aktif.is_(True),
        )
        .order_by(User.id)
    )
    if lock:
        accounts_query = accounts_query.with_for_update().execution_options(populate_existing=True)
    accounts = {row.id for row in db.scalars(accounts_query)}
    if accounts != active_ids:
        conflict("Roster Aktif memerlukan akun Mahasiswa aktif pada prodi yang sama")
    members = {klass.id: set() for klass in ctx.classes}
    for row, profile in rows:
        klass = db.get(KelasPeriode, row.kelas_periode_id)
        if (
            profile.angkatan_id != ctx.cohort.id
            or klass.angkatan_id != ctx.cohort.id
            or klass.periode_id != ctx.periode.id
            or (row.status == "Aktif") != (klass.kode_kelas != "K")
        ):
            conflict("Roster tidak sesuai angkatan, kelas, atau status akademik")
        if row.status == "Aktif":
            if klass.id not in members:
                conflict("Kelas roster tidak termasuk kelas reguler angkatan")
            members[klass.id].add(row.mahasiswa_id)
    return members


def existing_offerings(db, ctx, *, lock=False):
    class_ids = select(KelasPeriode.id).where(
        KelasPeriode.periode_id == ctx.periode.id, KelasPeriode.angkatan_id == ctx.cohort.id
    )
    query = select(KelasMK).where(KelasMK.kelas_periode_id.in_(class_ids)).order_by(KelasMK.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    rows = list(db.scalars(query))
    pairs = {(klass.id, course.id) for klass in ctx.classes for course in ctx.courses}
    result = {}
    for row in rows:
        if (row.kelas_periode_id, row.kurikulum_mk_id) not in pairs:
            conflict("Perkuliahan yang sudah ada tidak sesuai paket semester/kelas reguler")
        design = db.get(RancanganPenilaian, row.rancangan_id)
        if design.periode_id != ctx.periode.id or design.kurikulum_mk_id != row.kurikulum_mk_id:
            conflict("Konteks rancangan perkuliahan tidak sesuai")
        result[row.kelas_periode_id, row.kurikulum_mk_id] = row
    return result


def preview(db, user, periode_id, angkatan_id):
    ctx = context(db, user, periode_id, angkatan_id)
    members = active_roster(db, user, ctx)
    existing = existing_offerings(db, ctx)
    pairs = []
    for klass in ctx.classes:
        for course in ctx.courses:
            offering = existing.get((klass.id, course.id))
            design = db.get(RancanganPenilaian, offering.rancangan_id) if offering else None
            pairs.append(
                dict(
                    kelas_periode_id=klass.id,
                    kurikulum_mk_id=course.id,
                    kelas_mk_id=offering.id if offering else None,
                    dosen_id=design.dosen_id if design else None,
                    rancangan_id=design.id if design else None,
                )
            )
    return PackagePreview(
        periode_id=ctx.periode.id,
        angkatan_id=ctx.cohort.id,
        kurikulum_id=ctx.kurikulum.id,
        semester_studi=ctx.semester,
        kelas=[
            dict(
                kelas_periode_id=klass.id,
                kode_kelas=klass.kode_kelas,
                label=academic.class_response(db, user, klass)["label"],
                jumlah_mahasiswa_aktif=len(members[klass.id]),
            )
            for klass in ctx.classes
        ],
        mata_kuliah=[
            dict(
                kurikulum_mk_id=course.id,
                mk_id=course.mk_id,
                kode_mk=ctx.masters[course.id].kode_mk,
                nama_mk=course.nama_mk,
                sks=course.sks,
            )
            for course in ctx.courses
        ],
        penugasan=pairs,
    )


def shared_design(db, user, ctx, mk_id, dosen_id):
    row = db.scalar(
        select(RancanganPenilaian)
        .where(
            RancanganPenilaian.periode_id == ctx.periode.id,
            RancanganPenilaian.kurikulum_mk_id == mk_id,
            RancanganPenilaian.dosen_id == dosen_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is not None:
        return row, False
    row = RancanganPenilaian(periode_id=ctx.periode.id, kurikulum_mk_id=mk_id, dosen_id=dosen_id)
    db.add(row)
    db.flush()
    academic.record(db, user, "create", row, periode_id=ctx.periode.id)
    return row, True


def assign(db, user, ctx, row, dosen_id):
    current = db.get(RancanganPenilaian, row.rancangan_id)
    if current.dosen_id == dosen_id:
        return False, False
    if db.scalar(select(NilaiMahasiswa.id).where(NilaiMahasiswa.kelas_mk_id == row.id).limit(1)):
        conflict("Kelas sudah memiliki nilai; dosen pengampu tidak dapat diganti")
    before = snapshot(row)
    design, created = shared_design(db, user, ctx, row.kurikulum_mk_id, dosen_id)
    row.rancangan_id = design.id
    academic.record(db, user, "change_lecturer", row, before, periode_id=ctx.periode.id)
    return True, created


def apply(db: Session, user: User, periode_id: UUID, angkatan_id: UUID, payload):
    with transaction(db):
        ctx = context(db, user, periode_id, angkatan_id, edit=True)
        expected = {(klass.id, course.id) for klass in ctx.classes for course in ctx.courses}
        requested = {
            (item.kelas_periode_id, item.kurikulum_mk_id): item.dosen_id
            for item in payload.penugasan
        }
        if requested.keys() - expected:
            raise HTTPException(404, "Penugasan di luar kelas/paket angkatan pada periode ini")
        if expected - requested.keys():
            conflict("Lengkapi satu dosen untuk setiap pasangan kelas reguler dan MK paket")
        lecturers(db, user, set(requested.values()), lock=True)
        members = active_roster(db, user, ctx, lock=True)
        existing = existing_offerings(db, ctx, lock=True)
        counts = dict(
            kelas_mk_dibuat=0, kelas_mk_diperbarui=0, rancangan_dibuat=0, peserta_ditambahkan=0
        )
        courses = {course.id: course for course in ctx.courses}
        total_students = 0
        for pair in sorted(expected):
            class_id, mk_id = pair
            row = existing.get(pair)
            if row is None:
                design, created = shared_design(db, user, ctx, mk_id, requested[pair])
                row = KelasMK(
                    kelas_periode_id=class_id, kurikulum_mk_id=mk_id, rancangan_id=design.id
                )
                db.add(row)
                db.flush()
                academic.record(db, user, "create", row, periode_id=ctx.periode.id)
                counts["kelas_mk_dibuat"] += 1
                counts["rancangan_dibuat"] += int(created)
            else:
                changed, created = assign(db, user, ctx, row, requested[pair])
                counts["kelas_mk_diperbarui"] += int(changed)
                counts["rancangan_dibuat"] += int(created)
            current_members = {
                person.mahasiswa_id: person
                for person in db.scalars(
                    select(PesertaKelasMK).where(PesertaKelasMK.kelas_mk_id == row.id)
                )
            }
            if current_members.keys() - members[class_id] or any(
                person.mk_id != courses[mk_id].mk_id for person in current_members.values()
            ):
                conflict(
                    "Peserta perkuliahan tidak sesuai roster; koreksi penempatan terlebih dahulu"
                )
            for student_id in sorted(members[class_id] - current_members.keys()):
                person = PesertaKelasMK(
                    kelas_mk_id=row.id, mahasiswa_id=student_id, mk_id=courses[mk_id].mk_id
                )
                db.add(person)
                db.flush()
                academic.record(
                    db,
                    user,
                    "add_participant",
                    row,
                    periode_id=ctx.periode.id,
                    after={"peserta": snapshot(person)},
                )
                counts["peserta_ditambahkan"] += 1
            total_students += len(members[class_id])
        result = PackageResult(
            periode_id=ctx.periode.id,
            angkatan_id=ctx.cohort.id,
            kurikulum_id=ctx.kurikulum.id,
            semester_studi=ctx.semester,
            total_kelas_mk=len(expected),
            total_peserta=total_students,
            **counts,
        )
        if any(counts.values()):
            academic.record(
                db,
                user,
                "apply_package",
                ctx.cohort,
                periode_id=ctx.periode.id,
                after=result.model_dump(mode="json"),
            )
    return result


def change_lecturer(db, user, kelas_mk_id, payload):
    with transaction(db):
        initial = require_class_access(db, user, kelas_mk_id)
        klass = initial[1]
        ctx = context(db, user, klass.periode_id, klass.angkatan_id, edit=True)
        lecturers(db, user, {payload.dosen_id}, lock=True)
        rows = existing_offerings(db, ctx, lock=True)
        row = next((row for row in rows.values() if row.id == kelas_mk_id), None)
        if row is None:
            raise HTTPException(404, "Kelas MK tidak ditemukan")
        assign(db, user, ctx, row, payload.dosen_id)
        design = db.get(RancanganPenilaian, row.rancangan_id)
        result = AssignmentResponse(
            kelas_mk_id=row.id,
            kelas_periode_id=row.kelas_periode_id,
            kurikulum_mk_id=row.kurikulum_mk_id,
            periode_id=ctx.periode.id,
            dosen_id=design.dosen_id,
            rancangan_id=design.id,
        )
    return result
