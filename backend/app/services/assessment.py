"""Shared lecturer assessment design, Decimal readiness, and immutable grade history."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, func, select

from app.models import (
    CPMK,
    CPMKCPL,
    MKCPL,
    InstrumenPenilaian,
    KelasMK,
    KelasPeriode,
    Kurikulum,
    KurikulumMK,
    MasterCPL,
    NilaiMahasiswa,
    PeriodeAkademik,
    Prodi,
    RancanganPenilaian,
    SubCPMK,
)
from app.schemas.assessment import DesignDetail, DesignSummary
from app.services import academic
from app.services.access import require_class_access
from app.services.curriculum import conflict, owned, snapshot, transaction


def access_query(user):
    if user.role != "Dosen":
        raise HTTPException(403, "Rancangan penilaian hanya dapat dikelola Dosen")
    assigned = (
        select(KelasMK.id)
        .join(KelasPeriode, KelasMK.kelas_periode_id == KelasPeriode.id)
        .where(
            KelasMK.rancangan_id == RancanganPenilaian.id,
            KelasMK.kurikulum_mk_id == RancanganPenilaian.kurikulum_mk_id,
            KelasPeriode.periode_id == RancanganPenilaian.periode_id,
        )
        .exists()
    )
    return (
        select(RancanganPenilaian)
        .join(PeriodeAkademik, RancanganPenilaian.periode_id == PeriodeAkademik.id)
        .join(KurikulumMK, RancanganPenilaian.kurikulum_mk_id == KurikulumMK.id)
        .join(Kurikulum, KurikulumMK.kurikulum_id == Kurikulum.id)
        .where(
            RancanganPenilaian.dosen_id == user.id,
            PeriodeAkademik.prodi_id == user.prodi_id,
            Kurikulum.prodi_id == user.prodi_id,
            assigned,
        )
    )


def design(db, user, entity_id, *, lock=False):
    query = access_query(user).where(RancanganPenilaian.id == entity_id)
    if lock:
        query = query.with_for_update(of=RancanganPenilaian).execution_options(
            populate_existing=True
        )
    row = db.scalar(query)
    if row is None:
        raise HTTPException(404, "Rancangan tidak ditemukan pada kelas penugasan")
    return row


def has_grades(db, design_id):
    by_class = (
        select(NilaiMahasiswa.id)
        .join(KelasMK, NilaiMahasiswa.kelas_mk_id == KelasMK.id)
        .where(KelasMK.rancangan_id == design_id)
        .limit(1)
    )
    by_instrument = (
        select(NilaiMahasiswa.id)
        .join(InstrumenPenilaian, NilaiMahasiswa.instrumen_id == InstrumenPenilaian.id)
        .join(SubCPMK, InstrumenPenilaian.sub_cpmk_id == SubCPMK.id)
        .join(CPMK, SubCPMK.cpmk_id == CPMK.id)
        .where(CPMK.rancangan_id == design_id)
        .limit(1)
    )
    return db.scalar(by_class) is not None or db.scalar(by_instrument) is not None


def editable(db, user, entity_id):
    initial = design(db, user, entity_id)
    academic.period(db, user, initial.periode_id, edit=True)
    row = design(db, user, entity_id, lock=True)  # Recheck assignment after waiting for the period.
    if has_grades(db, row.id):
        conflict("Struktur rancangan bersama dibekukan karena sudah ada nilai")
    return row


def instrument_query(design_id):
    return (
        select(InstrumenPenilaian)
        .join(SubCPMK, InstrumenPenilaian.sub_cpmk_id == SubCPMK.id)
        .join(CPMK, SubCPMK.cpmk_id == CPMK.id)
        .where(CPMK.rancangan_id == design_id)
    )


def total_weight(db, design_id):
    value = db.scalar(
        instrument_query(design_id).with_only_columns(
            func.coalesce(func.sum(InstrumenPenilaian.bobot_persentase), 0)
        )
    )
    return Decimal(value).quantize(Decimal("0.01"))


def allowed_cpl(db, row, user):
    mk = db.get(KurikulumMK, row.kurikulum_mk_id)
    return list(
        db.scalars(
            select(MasterCPL)
            .join(MKCPL, MKCPL.cpl_id == MasterCPL.id)
            .where(
                MKCPL.kurikulum_mk_id == mk.id,
                MasterCPL.kurikulum_id == mk.kurikulum_id,
                (MasterCPL.prodi_id == user.prodi_id) | MasterCPL.prodi_id.is_(None),
            )
            .order_by(MasterCPL.kode_cpl, MasterCPL.id)
        )
    )


def validate_cpl(db, row, user, ids):
    permitted = {cpl.id for cpl in allowed_cpl(db, row, user)}
    if set(ids) - permitted:
        raise HTTPException(404, "CPL tidak dibebankan pada MK/versi kurikulum rancangan ini")


def cpmk_row(db, design_id, cpmk_id):
    row = db.scalar(
        select(CPMK)
        .where(CPMK.id == cpmk_id, CPMK.rancangan_id == design_id)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404, "CPMK tidak ditemukan pada rancangan ini")
    return row


def sub_row(db, design_id, cpmk_id, sub_id):
    cpmk_row(db, design_id, cpmk_id)
    row = db.scalar(
        select(SubCPMK)
        .where(SubCPMK.id == sub_id, SubCPMK.cpmk_id == cpmk_id)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404, "Sub-CPMK tidak ditemukan pada CPMK ini")
    return row


def instrument_row(db, design_id, cpmk_id, sub_id, instrument_id):
    sub_row(db, design_id, cpmk_id, sub_id)
    row = db.scalar(
        select(InstrumenPenilaian)
        .where(InstrumenPenilaian.id == instrument_id, InstrumenPenilaian.sub_cpmk_id == sub_id)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404, "Instrumen tidak ditemukan pada Sub-CPMK ini")
    return row


def row_snapshot(row):
    return {
        key: format(value, ".2f") if isinstance(value, Decimal) else value
        for key, value in snapshot(row).items()
    }


def sub_view(db, row):
    return {
        **snapshot(row),
        "instrumen": [
            row_snapshot(i)
            for i in db.scalars(
                select(InstrumenPenilaian)
                .where(InstrumenPenilaian.sub_cpmk_id == row.id)
                .order_by(InstrumenPenilaian.nama_instrumen, InstrumenPenilaian.id)
            )
        ],
    }


def cpmk_view(db, row):
    return {
        **snapshot(row),
        "cpl_ids": list(
            db.scalars(
                select(CPMKCPL.cpl_id).where(CPMKCPL.cpmk_id == row.id).order_by(CPMKCPL.cpl_id)
            )
        ),
        "sub_cpmk": [
            sub_view(db, sub)
            for sub in db.scalars(
                select(SubCPMK)
                .where(SubCPMK.cpmk_id == row.id)
                .order_by(SubCPMK.kode_sub, SubCPMK.id)
            )
        ],
    }


def summary(db, user, row):
    periode = academic.period(db, user, row.periode_id)
    cpmks = list(
        db.scalars(
            select(CPMK).where(CPMK.rancangan_id == row.id).order_by(CPMK.kode_cpmk, CPMK.id)
        )
    )
    permitted = {cpl.id for cpl in allowed_cpl(db, row, user)}
    reasons = []
    if not cpmks:
        reasons.append("Belum ada CPMK")
    for cpmk in cpmks:
        mapped = set(db.scalars(select(CPMKCPL.cpl_id).where(CPMKCPL.cpmk_id == cpmk.id)))
        if not mapped or mapped - permitted:
            reasons.append(f"{cpmk.kode_cpmk}: pemetaan CPL belum lengkap/valid")
    weight = total_weight(db, row.id)
    if weight != Decimal("100.00"):
        reasons.append("Total bobot instrumen belum 100.00%")
    grades = has_grades(db, row.id)
    closed = periode.status == "Ditutup"
    prodi = db.get(Prodi, user.prodi_id)
    classes = db.execute(
        select(KelasMK, KelasPeriode)
        .join(KelasPeriode, KelasMK.kelas_periode_id == KelasPeriode.id)
        .where(
            KelasMK.rancangan_id == row.id,
            KelasPeriode.periode_id == row.periode_id,
            KelasMK.kurikulum_mk_id == row.kurikulum_mk_id,
        )
        .order_by(KelasPeriode.kode_kelas, KelasMK.id)
    ).all()
    return DesignSummary(
        **snapshot(row),
        tahun_akademik=periode.tahun_akademik,
        semester=periode.semester,
        total_bobot=weight,
        siap_dinilai=not reasons,
        boleh_input_nilai=not reasons and not closed,
        alasan_belum_siap=reasons,
        sudah_ada_nilai=grades,
        periode_ditutup=closed,
        struktur_terkunci=closed or grades,
        alasan_terkunci="Periode ditutup"
        if closed
        else ("Sudah ada nilai pada kelas pengguna rancangan" if grades else None),
        kelas_pengguna=[
            dict(
                kelas_mk_id=mk.id,
                kelas_periode_id=klass.id,
                label=f"{prodi.kode_prodi}-{klass.tingkat}{klass.kode_kelas}",
            )
            for mk, klass in classes
        ],
    )


def detail(db, user, entity_id):
    row = design(db, user, entity_id)
    state = summary(db, user, row)
    return DesignDetail(
        **state.model_dump(),
        cpl_tersedia=allowed_cpl(db, row, user),
        cpmk=[
            cpmk_view(db, c)
            for c in db.scalars(
                select(CPMK).where(CPMK.rancangan_id == row.id).order_by(CPMK.kode_cpmk, CPMK.id)
            )
        ],
    )


def list_designs(db, user, periode_id, offset, limit):
    query = access_query(user)
    if periode_id is not None:
        academic.period(db, user, periode_id)
        query = query.where(RancanganPenilaian.periode_id == periode_id)
    rows = db.scalars(
        query.order_by(
            PeriodeAkademik.tahun_mulai.desc(),
            PeriodeAkademik.semester.desc(),
            RancanganPenilaian.id,
        )
        .offset(offset)
        .limit(limit)
    )
    return [summary(db, user, row) for row in rows]


def class_design(db, user, kelas_mk_id):
    row = require_class_access(db, user, kelas_mk_id)
    return detail(db, user, row[0].rancangan_id)


def set_cpl(db, row, ids):
    existing = set(db.scalars(select(CPMKCPL.cpl_id).where(CPMKCPL.cpmk_id == row.id)))
    removed = existing - set(ids)
    if removed:
        db.execute(delete(CPMKCPL).where(CPMKCPL.cpmk_id == row.id, CPMKCPL.cpl_id.in_(removed)))
    for cpl_id in set(ids) - existing:
        db.add(CPMKCPL(cpmk_id=row.id, cpl_id=cpl_id))
    db.flush()


def create_cpmk(db, user, design_id, payload):
    with transaction(db):
        parent = editable(db, user, design_id)
        validate_cpl(db, parent, user, payload.cpl_ids)
        values = payload.model_dump(exclude={"cpl_ids"})
        row = CPMK(rancangan_id=parent.id, **values)
        db.add(row)
        db.flush()
        set_cpl(db, row, payload.cpl_ids)
        academic.record(
            db, user, "create", row, periode_id=parent.periode_id, after=cpmk_view(db, row)
        )
    return cpmk_view(db, row)


def update_cpmk(db, user, design_id, cpmk_id, payload):
    with transaction(db):
        parent = editable(db, user, design_id)
        row = cpmk_row(db, design_id, cpmk_id)
        before = cpmk_view(db, row)
        changes = payload.model_dump(exclude_unset=True)
        if "cpl_ids" in changes:
            validate_cpl(db, parent, user, changes["cpl_ids"])
            set_cpl(db, row, changes.pop("cpl_ids"))
        for key, value in changes.items():
            setattr(row, key, value)
        academic.record(
            db, user, "update", row, before, periode_id=parent.periode_id, after=cpmk_view(db, row)
        )
    return cpmk_view(db, row)


def replace_cpl(db, user, design_id, cpmk_id, payload):
    with transaction(db):
        parent = editable(db, user, design_id)
        row = cpmk_row(db, design_id, cpmk_id)
        validate_cpl(db, parent, user, payload.cpl_ids)
        before = cpmk_view(db, row)
        set_cpl(db, row, payload.cpl_ids)
        academic.record(
            db,
            user,
            "replace_cpl",
            row,
            before,
            periode_id=parent.periode_id,
            after=cpmk_view(db, row),
        )
    return cpmk_view(db, row)


def delete_cpmk(db, user, design_id, cpmk_id):
    with transaction(db):
        parent = editable(db, user, design_id)
        row = cpmk_row(db, design_id, cpmk_id)
        academic.record(db, user, "delete", row, cpmk_view(db, row), periode_id=parent.periode_id)
        db.delete(row)


def create_sub(db, user, design_id, cpmk_id, payload):
    with transaction(db):
        parent = editable(db, user, design_id)
        cpmk_row(db, design_id, cpmk_id)
        row = SubCPMK(cpmk_id=cpmk_id, **payload.model_dump())
        db.add(row)
        db.flush()
        academic.record(
            db, user, "create", row, periode_id=parent.periode_id, after=sub_view(db, row)
        )
    return sub_view(db, row)


def update_sub(db, user, design_id, cpmk_id, sub_id, payload):
    with transaction(db):
        parent = editable(db, user, design_id)
        row = sub_row(db, design_id, cpmk_id, sub_id)
        before = sub_view(db, row)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        academic.record(
            db, user, "update", row, before, periode_id=parent.periode_id, after=sub_view(db, row)
        )
    return sub_view(db, row)


def delete_sub(db, user, design_id, cpmk_id, sub_id):
    with transaction(db):
        parent = editable(db, user, design_id)
        row = sub_row(db, design_id, cpmk_id, sub_id)
        academic.record(db, user, "delete", row, sub_view(db, row), periode_id=parent.periode_id)
        db.delete(row)


def check_weight(db, design_id, new_weight, old_weight=Decimal("0")):
    if total_weight(db, design_id) - old_weight + new_weight > Decimal("100.00"):
        conflict("Total bobot seluruh instrumen rancangan tidak boleh melebihi 100.00%")


def create_instrument(db, user, design_id, cpmk_id, sub_id, payload):
    with transaction(db):
        parent = editable(db, user, design_id)
        sub_row(db, design_id, cpmk_id, sub_id)
        check_weight(db, design_id, payload.bobot_persentase)
        row = InstrumenPenilaian(sub_cpmk_id=sub_id, **payload.model_dump())
        db.add(row)
        db.flush()
        academic.record(
            db, user, "create", row, periode_id=parent.periode_id, after=row_snapshot(row)
        )
    return row


def update_instrument(db, user, design_id, cpmk_id, sub_id, instrument_id, payload):
    with transaction(db):
        parent = editable(db, user, design_id)
        row = instrument_row(db, design_id, cpmk_id, sub_id, instrument_id)
        changes = payload.model_dump(exclude_unset=True)
        check_weight(
            db,
            design_id,
            changes.get("bobot_persentase", row.bobot_persentase),
            row.bobot_persentase,
        )
        before = row_snapshot(row)
        for key, value in changes.items():
            setattr(row, key, value)
        academic.record(
            db, user, "update", row, before, periode_id=parent.periode_id, after=row_snapshot(row)
        )
    return row


def delete_instrument(db, user, design_id, cpmk_id, sub_id, instrument_id):
    with transaction(db):
        parent = editable(db, user, design_id)
        row = instrument_row(db, design_id, cpmk_id, sub_id, instrument_id)
        academic.record(db, user, "delete", row, row_snapshot(row), periode_id=parent.periode_id)
        db.delete(row)


def copy_design(db, user, target_id, payload):
    with transaction(db):
        target = design(db, user, target_id)
        source = design(db, user, payload.sumber_rancangan_id)
        if (
            source.periode_id == target.periode_id
            or source.kurikulum_mk_id != target.kurikulum_mk_id
        ):
            conflict("Salin hanya antarperiode berbeda pada MK kurikulum yang sama")
        # Lock both periods before either design, always in UUID order. Source may be closed.
        periods = {
            p: owned(db, PeriodeAkademik, p, user, lock=True)
            for p in sorted({source.periode_id, target.periode_id})
        }
        if periods[target.periode_id].status != "Dibuka":
            conflict("Periode tujuan ditutup")
        locked = {key: design(db, user, key, lock=True) for key in sorted({source.id, target.id})}
        source, target = locked[source.id], locked[target.id]
        if has_grades(db, target.id) or db.scalar(
            select(CPMK.id).where(CPMK.rancangan_id == target.id).limit(1)
        ):
            conflict("Salin memerlukan rancangan tujuan kosong tanpa CPMK atau nilai")
        if total_weight(db, source.id) > Decimal("100.00"):
            conflict("Total bobot sumber tidak valid")
        before = snapshot(target)
        for cpmk in db.scalars(
            select(CPMK).where(CPMK.rancangan_id == source.id).order_by(CPMK.id)
        ):
            ids = list(db.scalars(select(CPMKCPL.cpl_id).where(CPMKCPL.cpmk_id == cpmk.id)))
            validate_cpl(db, target, user, ids)
            copied_cpmk = CPMK(
                rancangan_id=target.id, kode_cpmk=cpmk.kode_cpmk, deskripsi=cpmk.deskripsi
            )
            db.add(copied_cpmk)
            db.flush()
            set_cpl(db, copied_cpmk, ids)
            for sub in db.scalars(
                select(SubCPMK).where(SubCPMK.cpmk_id == cpmk.id).order_by(SubCPMK.id)
            ):
                copied_sub = SubCPMK(
                    cpmk_id=copied_cpmk.id, kode_sub=sub.kode_sub, deskripsi=sub.deskripsi
                )
                db.add(copied_sub)
                db.flush()
                for instrument in db.scalars(
                    select(InstrumenPenilaian)
                    .where(InstrumenPenilaian.sub_cpmk_id == sub.id)
                    .order_by(InstrumenPenilaian.id)
                ):
                    db.add(
                        InstrumenPenilaian(
                            sub_cpmk_id=copied_sub.id,
                            nama_instrumen=instrument.nama_instrumen,
                            jenis_instrumen=instrument.jenis_instrumen,
                            bobot_persentase=instrument.bobot_persentase,
                        )
                    )
        target.sumber_rancangan_id = source.id
        db.flush()
        academic.record(
            db,
            user,
            "copy_design",
            target,
            before,
            periode_id=target.periode_id,
            after=detail(db, user, target.id).model_dump(mode="json"),
        )
    return detail(db, user, target.id)


def get_cpmk(db, user, design_id, cpmk_id):
    design(db, user, design_id)
    return cpmk_view(db, cpmk_row(db, design_id, cpmk_id))


def list_cpmk(db, user, design_id, offset, limit):
    design(db, user, design_id)
    return [
        cpmk_view(db, row)
        for row in db.scalars(
            select(CPMK)
            .where(CPMK.rancangan_id == design_id)
            .order_by(CPMK.kode_cpmk, CPMK.id)
            .offset(offset)
            .limit(limit)
        )
    ]


def get_sub(db, user, design_id, cpmk_id, sub_id):
    design(db, user, design_id)
    return sub_view(db, sub_row(db, design_id, cpmk_id, sub_id))


def list_sub(db, user, design_id, cpmk_id, offset, limit):
    design(db, user, design_id)
    cpmk_row(db, design_id, cpmk_id)
    return [
        sub_view(db, row)
        for row in db.scalars(
            select(SubCPMK)
            .where(SubCPMK.cpmk_id == cpmk_id)
            .order_by(SubCPMK.kode_sub, SubCPMK.id)
            .offset(offset)
            .limit(limit)
        )
    ]


def get_instrument(db, user, design_id, cpmk_id, sub_id, instrument_id):
    design(db, user, design_id)
    return instrument_row(db, design_id, cpmk_id, sub_id, instrument_id)


def list_instrument(db, user, design_id, cpmk_id, sub_id, offset, limit):
    design(db, user, design_id)
    sub_row(db, design_id, cpmk_id, sub_id)
    return list(
        db.scalars(
            select(InstrumenPenilaian)
            .where(InstrumenPenilaian.sub_cpmk_id == sub_id)
            .order_by(InstrumenPenilaian.nama_instrumen, InstrumenPenilaian.id)
            .offset(offset)
            .limit(limit)
        )
    )
