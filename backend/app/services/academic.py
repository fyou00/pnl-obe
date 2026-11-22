"""Academic history and cohort/period/roster consistency, under explicit row locks."""

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select

from app.models import (
    Angkatan,
    AuditLog,
    KelasMK,
    KelasPeriode,
    Kurikulum,
    KurikulumMK,
    Mahasiswa,
    MahasiswaPeriode,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    Prodi,
    RancanganPenilaian,
    User,
)
from app.services.curriculum import conflict, owned, snapshot, transaction


def record(db, user, action, row, before=None, *, periode_id=None, after=None):
    db.flush()
    db.add(
        AuditLog(
            aktor_id=user.id,
            periode_id=periode_id,
            aksi=action,
            entitas=row.__tablename__,
            entitas_id=row.id,
            sebelum=jsonable_encoder(before),
            sesudah=jsonable_encoder(
                after if after is not None else (snapshot(row) if action != "delete" else None)
            ),
        )
    )


def period(db, user, periode_id, *, edit=False):
    row = owned(db, PeriodeAkademik, periode_id, user, lock=edit)
    if edit and row.status != "Dibuka":
        conflict("Periode ditutup; data akademik tidak dapat diubah")
    return row


def active_curriculum(db, user, curriculum_id):
    row = owned(db, Kurikulum, curriculum_id, user, lock=True)
    if row.status != "Aktif":
        conflict("Angkatan baru/perubahan kurikulum memerlukan kurikulum Aktif")
    return row


def list_angkatan(db, user, offset, limit, tahun):
    query = select(Angkatan).where(Angkatan.prodi_id == user.prodi_id)
    if tahun is not None:
        query = query.where(Angkatan.tahun_masuk == tahun)
    return list(
        db.scalars(
            query.order_by(Angkatan.tahun_masuk.desc(), Angkatan.id).offset(offset).limit(limit)
        )
    )


def create_angkatan(db, user, payload):
    with transaction(db):
        active_curriculum(db, user, payload.kurikulum_id)
        row = Angkatan(prodi_id=user.prodi_id, **payload.model_dump())
        db.add(row)
        db.flush()
        record(db, user, "create", row)
    return row


def update_angkatan(db, user, entity_id, payload):
    with transaction(db):
        row = owned(db, Angkatan, entity_id, user, lock=True)
        before = snapshot(row)
        changes = payload.model_dump(exclude_unset=True)
        if any(getattr(row, key) != value for key, value in changes.items()):
            period_ids = sorted(
                set(
                    db.scalars(
                        select(KelasPeriode.periode_id).where(KelasPeriode.angkatan_id == row.id)
                    )
                )
            )
            for period_id in period_ids:
                period(db, user, period_id, edit=True)
        classes = select(KelasPeriode.id).where(KelasPeriode.angkatan_id == row.id)
        if changes.get("tahun_masuk", row.tahun_masuk) != row.tahun_masuk and (
            db.scalar(select(Mahasiswa.id).where(Mahasiswa.angkatan_id == row.id).limit(1))
            or db.scalar(classes.limit(1))
        ):
            conflict("Tahun masuk angkatan yang sudah memiliki mahasiswa/kelas tidak dapat diganti")
        if changes.get("kurikulum_id", row.kurikulum_id) != row.kurikulum_id:
            if db.scalar(select(KelasMK.id).where(KelasMK.kelas_periode_id.in_(classes)).limit(1)):
                conflict("Kurikulum angkatan dibekukan setelah paket diterapkan")
            active_curriculum(db, user, changes["kurikulum_id"])
        for key, value in changes.items():
            setattr(row, key, value)
        record(db, user, "update", row, before)
    return row


def delete_angkatan(db, user, entity_id):
    with transaction(db):
        row = owned(db, Angkatan, entity_id, user, lock=True)
        record(db, user, "delete", row, snapshot(row))
        db.delete(row)  # RESTRICT retains linked students/classes/history.


def list_periods(db, user, offset, limit, tahun, semester):
    query = select(PeriodeAkademik).where(PeriodeAkademik.prodi_id == user.prodi_id)
    if tahun is not None:
        query = query.where(PeriodeAkademik.tahun_mulai == tahun)
    if semester:
        query = query.where(PeriodeAkademik.semester == semester)
    return list(
        db.scalars(
            query.order_by(
                PeriodeAkademik.tahun_mulai.desc(), PeriodeAkademik.semester, PeriodeAkademik.id
            )
            .offset(offset)
            .limit(limit)
        )
    )


def create_period(db, user, payload):
    with transaction(db):
        row = PeriodeAkademik(prodi_id=user.prodi_id, status="Dibuka", **payload.model_dump())
        db.add(row)
        db.flush()
        record(db, user, "create", row)
    return row


def update_period(db, user, entity_id, payload):
    with transaction(db):
        row = period(db, user, entity_id, edit=True)
        changes = payload.model_dump(exclude_unset=True)
        if any(getattr(row, key) != value for key, value in changes.items()) and (
            db.scalar(select(KelasPeriode.id).where(KelasPeriode.periode_id == row.id).limit(1))
            or db.scalar(
                select(RancanganPenilaian.id)
                .where(RancanganPenilaian.periode_id == row.id)
                .limit(1)
            )
        ):
            conflict("Identitas periode yang sudah digunakan tidak dapat diubah")
        before = snapshot(row)
        for key, value in changes.items():
            setattr(row, key, value)
        record(db, user, "update", row, before)
    return row


def delete_period(db, user, entity_id):
    with transaction(db):
        row = period(db, user, entity_id, edit=True)
        if (
            db.scalar(select(KelasPeriode.id).where(KelasPeriode.periode_id == row.id).limit(1))
            or db.scalar(
                select(RancanganPenilaian.id)
                .where(RancanganPenilaian.periode_id == row.id)
                .limit(1)
            )
            or db.scalar(select(AuditLog.id).where(AuditLog.periode_id == row.id).limit(1))
        ):
            conflict("Periode sudah mempunyai kegiatan/riwayat akademik; tidak dapat dihapus")
        record(db, user, "delete", row, snapshot(row))
        db.delete(row)


def class_in_period(db, periode_id, entity_id):
    row = db.scalar(
        select(KelasPeriode)
        .where(KelasPeriode.id == entity_id, KelasPeriode.periode_id == periode_id)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404, "Kelas tidak ditemukan pada periode ini")
    return row


def validate_class(db, user, cohort, periode, code, semester, entity_id=None):
    if periode.tahun_mulai < cohort.tahun_masuk:
        conflict("Periode tidak boleh mendahului tahun masuk angkatan")
    if code == "K":
        if semester is not None:
            conflict("Kelas K wajib semester studi null")
    else:
        if semester is None or not 1 <= semester <= 8:
            conflict("Kelas reguler membutuhkan semester studi 1–8")
        if semester % 2 != (1 if periode.semester == "Ganjil" else 0):
            conflict("Semester studi tidak sesuai Ganjil/Genap periode")
        query = select(KelasPeriode.id).where(
            KelasPeriode.periode_id == periode.id,
            KelasPeriode.angkatan_id == cohort.id,
            KelasPeriode.kode_kelas != "K",
            KelasPeriode.semester_studi != semester,
        )
        if entity_id:
            query = query.where(KelasPeriode.id != entity_id)
        if db.scalar(query.limit(1)):
            conflict("Kelas reguler satu angkatan/periode harus memiliki semester studi yang sama")


def class_response(db, user, row):
    prodi = db.get(Prodi, user.prodi_id)
    values = {
        attr: getattr(row, attr)
        for attr in ["id", "periode_id", "angkatan_id", "kode_kelas", "semester_studi", "tingkat"]
    }
    values["label"] = (
        f"{prodi.kode_prodi}-K"
        if row.kode_kelas == "K"
        else f"{prodi.kode_prodi}-{row.tingkat}{row.kode_kelas}"
    )
    return values


def list_classes(db, user, periode_id, offset, limit, angkatan_id):
    period(db, user, periode_id)
    query = select(KelasPeriode).where(KelasPeriode.periode_id == periode_id)
    if angkatan_id:
        owned(db, Angkatan, angkatan_id, user)
        query = query.where(KelasPeriode.angkatan_id == angkatan_id)
    rows = db.scalars(
        query.order_by(KelasPeriode.angkatan_id, KelasPeriode.kode_kelas, KelasPeriode.id)
        .offset(offset)
        .limit(limit)
    )
    return [class_response(db, user, row) for row in rows]


def create_class(db, user, periode_id, payload):
    with transaction(db):
        cohort = owned(db, Angkatan, payload.angkatan_id, user, lock=True)
        periode = period(db, user, periode_id, edit=True)
        validate_class(db, user, cohort, periode, payload.kode_kelas, payload.semester_studi)
        row = KelasPeriode(periode_id=periode.id, **payload.model_dump())
        db.add(row)
        db.flush()
        record(db, user, "create", row, periode_id=periode.id)
    return class_response(db, user, row)


def update_class(db, user, periode_id, entity_id, payload):
    with transaction(db):
        period(db, user, periode_id)
        row = class_in_period(db, periode_id, entity_id)
        cohort = owned(db, Angkatan, row.angkatan_id, user, lock=True)
        periode = period(db, user, periode_id, edit=True)
        row = class_in_period(db, periode_id, entity_id)
        changes = payload.model_dump(exclude_unset=True)
        code, semester = (
            changes.get("kode_kelas", row.kode_kelas),
            changes.get("semester_studi", row.semester_studi),
        )
        validate_class(db, user, cohort, periode, code, semester, row.id)
        if any(getattr(row, key) != value for key, value in changes.items()):
            if db.scalar(select(KelasMK.id).where(KelasMK.kelas_periode_id == row.id).limit(1)):
                conflict("Identitas kelas yang sudah mempunyai perkuliahan tidak dapat diubah")
            roster = list(
                db.scalars(
                    select(MahasiswaPeriode.status).where(
                        MahasiswaPeriode.kelas_periode_id == row.id
                    )
                )
            )
            if any((status == "Aktif") != (code != "K") for status in roster):
                conflict("Perubahan kelas tidak sesuai status mahasiswa yang masih ditempatkan")
        before = snapshot(row)
        for key, value in changes.items():
            setattr(row, key, value)
        record(db, user, "update", row, before, periode_id=periode.id)
    return class_response(db, user, row)


def delete_class(db, user, periode_id, entity_id):
    with transaction(db):
        period(db, user, periode_id)
        row = class_in_period(db, periode_id, entity_id)
        owned(db, Angkatan, row.angkatan_id, user, lock=True)
        period(db, user, periode_id, edit=True)
        row = class_in_period(db, periode_id, entity_id)
        record(db, user, "delete", row, snapshot(row), periode_id=periode_id)
        db.delete(row)


def student(db, user, student_id, *, lock=False):
    account = owned(db, User, student_id, user, lock=lock)
    profile = db.get(Mahasiswa, student_id)
    if account.role != "Mahasiswa" or profile is None:
        raise HTTPException(404, "Mahasiswa tidak ditemukan")
    owned(db, Angkatan, profile.angkatan_id, user)
    return profile, account


def list_students(db, user, angkatan_id, offset, limit):
    owned(db, Angkatan, angkatan_id, user)
    rows = db.execute(
        select(Mahasiswa, User)
        .join(User, User.id == Mahasiswa.id)
        .where(
            Mahasiswa.angkatan_id == angkatan_id,
            User.prodi_id == user.prodi_id,
            User.role == "Mahasiswa",
        )
        .order_by(User.nim_nidn, User.id)
        .offset(offset)
        .limit(limit)
    )
    return [
        dict(
            id=profile.id,
            angkatan_id=profile.angkatan_id,
            nim_nidn=account.nim_nidn,
            nama=account.nama,
            aktif=account.aktif,
        )
        for profile, account in rows
    ]


def link_student(db, user, angkatan_id, payload):
    with transaction(db):
        cohort = owned(db, Angkatan, angkatan_id, user, lock=True)
        account = owned(db, User, payload.user_id, user, lock=True)
        if account.role != "Mahasiswa" or not account.aktif:
            conflict("Akun harus Mahasiswa yang aktif")
        if db.get(Mahasiswa, account.id):
            conflict("Mahasiswa sudah terhubung dengan angkatan")
        row = Mahasiswa(id=account.id, angkatan_id=cohort.id)
        db.add(row)
        db.flush()
        record(db, user, "create", row)
    return dict(
        id=row.id,
        angkatan_id=row.angkatan_id,
        nim_nidn=account.nim_nidn,
        nama=account.nama,
        aktif=account.aktif,
    )


def roster(db, periode_id, student_id):
    row = db.scalar(
        select(MahasiswaPeriode)
        .where(
            MahasiswaPeriode.periode_id == periode_id, MahasiswaPeriode.mahasiswa_id == student_id
        )
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404, "Penempatan mahasiswa tidak ditemukan")
    return row


def list_roster(db, user, periode_id, offset, limit, kelas_id, status):
    period(db, user, periode_id)
    query = (
        select(MahasiswaPeriode)
        .join(User, MahasiswaPeriode.mahasiswa_id == User.id)
        .where(MahasiswaPeriode.periode_id == periode_id, User.prodi_id == user.prodi_id)
    )
    if kelas_id:
        class_in_period(db, periode_id, kelas_id)
        query = query.where(MahasiswaPeriode.kelas_periode_id == kelas_id)
    if status:
        query = query.where(MahasiswaPeriode.status == status)
    return list(
        db.scalars(query.order_by(MahasiswaPeriode.mahasiswa_id).offset(offset).limit(limit))
    )


def sync_participants(db, user, periode, profile, target_class, status):
    """Reconcile existing offerings only; never creates offerings/lecturer assignments."""
    query = (
        select(PesertaKelasMK)
        .join(KelasMK, PesertaKelasMK.kelas_mk_id == KelasMK.id)
        .join(KelasPeriode, KelasMK.kelas_periode_id == KelasPeriode.id)
        .where(PesertaKelasMK.mahasiswa_id == profile.id, KelasPeriode.periode_id == periode.id)
    )
    existing = list(db.scalars(query))
    existing_ids = [row.kelas_mk_id for row in existing]
    if existing_ids and db.scalar(
        select(NilaiMahasiswa.id)
        .where(
            NilaiMahasiswa.mahasiswa_id == profile.id, NilaiMahasiswa.kelas_mk_id.in_(existing_ids)
        )
        .limit(1)
    ):
        conflict("Mahasiswa sudah memiliki nilai pada periode ini; penempatan tidak dapat diubah")
    before = [snapshot(row) for row in existing]
    if existing_ids:
        db.execute(
            delete(PesertaKelasMK).where(
                PesertaKelasMK.mahasiswa_id == profile.id,
                PesertaKelasMK.kelas_mk_id.in_(existing_ids),
            )
        )
    if target_class is not None and status == "Aktif":
        cohort = db.get(Angkatan, profile.angkatan_id)
        courses = list(
            db.scalars(
                select(KelasMK)
                .where(KelasMK.kelas_periode_id == target_class.id)
                .order_by(KelasMK.id)
            )
        )
        for course in courses:
            mk = db.get(KurikulumMK, course.kurikulum_mk_id)
            design = db.get(RancanganPenilaian, course.rancangan_id)
            if (
                mk.kurikulum_id != cohort.kurikulum_id
                or mk.semester != target_class.semester_studi
                or design.periode_id != periode.id
                or design.kurikulum_mk_id != mk.id
            ):
                conflict("Konteks perkuliahan tujuan tidak konsisten")
            row = PesertaKelasMK(kelas_mk_id=course.id, mahasiswa_id=profile.id, mk_id=mk.mk_id)
            db.add(row)
        db.flush()  # UNIQUE rejects re-taking an MK from another period; rollback also restores old rows.
    return {"sebelum": before, "sesudah": [snapshot(row) for row in db.scalars(query)]}


def write_roster(db, user, periode_id, student_id, payload, *, create=False, remove=False):
    with transaction(db):
        period(db, user, periode_id)
        profile, account = student(db, user, student_id)
        cohort = owned(db, Angkatan, profile.angkatan_id, user, lock=True)
        periode = period(db, user, periode_id, edit=True)
        profile, account = student(db, user, student_id, lock=True)
        if create and db.scalar(
            select(MahasiswaPeriode.id).where(
                MahasiswaPeriode.periode_id == periode_id,
                MahasiswaPeriode.mahasiswa_id == student_id,
            )
        ):
            conflict("Mahasiswa sudah ditempatkan pada periode ini")
        current = None if create else roster(db, periode_id, student_id)
        before = snapshot(current) if current else None
        if remove:
            participation = sync_participants(db, user, periode, profile, None, None)
            record(
                db,
                user,
                "delete",
                current,
                before,
                periode_id=periode.id,
                after={"kepesertaan": participation},
            )
            db.delete(current)
        else:
            changes = payload.model_dump(exclude_unset=not create)
            kelas_id = changes.get(
                "kelas_periode_id", current.kelas_periode_id if current else None
            )
            status = changes.get("status", current.status if current else None)
            kelas = class_in_period(db, periode_id, kelas_id)
            if kelas.angkatan_id != cohort.id:
                conflict("Angkatan mahasiswa harus sama dengan angkatan kelas")
            if (status == "Aktif") != (kelas.kode_kelas != "K"):
                conflict("Aktif harus kelas A–E; Cuti/Nonaktif harus kelas K")
            if status == "Aktif" and not account.aktif:
                conflict("Akun mahasiswa nonaktif tidak dapat menerima penempatan Aktif")
            validate_class(
                db, user, cohort, periode, kelas.kode_kelas, kelas.semester_studi, kelas.id
            )
            row = current or MahasiswaPeriode(mahasiswa_id=profile.id, periode_id=periode.id)
            participation = None
            if create or row.kelas_periode_id != kelas_id or row.status != status:
                participation = sync_participants(db, user, periode, profile, kelas, status)
            row.kelas_periode_id, row.status = kelas_id, status
            db.add(row)
            db.flush()
            record(
                db,
                user,
                "create" if create else "update",
                row,
                before,
                periode_id=periode.id,
                after={**snapshot(row), "kepesertaan": participation},
            )
    return None if remove else row
