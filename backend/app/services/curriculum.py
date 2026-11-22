"""Master/curriculum invariants live here; routers never write ORM rows directly."""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, inspect, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    CPMK,
    CPMKCPL,
    MKCPL,
    Angkatan,
    AuditLog,
    KelasMK,
    Kurikulum,
    KurikulumMK,
    MasterCPL,
    MataKuliah,
    RancanganPenilaian,
    User,
)


def conflict(message: str):
    raise HTTPException(409, message)


@contextmanager
def transaction(db: Session) -> Iterator[None]:
    # Authentication already autobegins this Session; do not start a nested transaction.
    try:
        yield
        db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        conflict("Data duplikat atau masih direferensikan; perubahan dibatalkan")
    except Exception:
        db.rollback()
        raise


def snapshot(row) -> dict:
    return {
        attr.key: str(value) if isinstance(value := getattr(row, attr.key), UUID) else value
        for attr in inspect(row).mapper.column_attrs
    }


def audit(db: Session, user: User, action: str, row, before=None, after=None):
    db.flush()
    db.add(
        AuditLog(
            aktor_id=user.id,
            aksi=action,
            entitas=row.__tablename__,
            entitas_id=getattr(row, "id", None) or row.kurikulum_mk_id,
            sebelum=before,
            sesudah=after,
        )
    )


def owned(db: Session, model, entity_id: UUID, user: User, *, lock=False):
    query = select(model).where(model.id == entity_id, model.prodi_id == user.prodi_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = db.scalar(query)
    if row is None:
        raise HTTPException(404, "Data tidak ditemukan")
    return row


def curriculum(db: Session, user: User, curriculum_id: UUID, *, edit=False, lock=False):
    row = owned(db, Kurikulum, curriculum_id, user, lock=edit or lock)
    if edit and row.status != "Draft":
        conflict("Kurikulum Aktif/Arsip tidak dapat diubah; salin menjadi versi Draft baru")
    return row


def child(db: Session, model, entity_id: UUID, curriculum_id: UUID):
    row = db.scalar(select(model).where(model.id == entity_id, model.kurikulum_id == curriculum_id))
    if row is None:
        raise HTTPException(404, "Data tidak ditemukan pada kurikulum ini")
    return row


def search(query, columns, q):
    if q:
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(or_(*(column.ilike(pattern, escape="\\") for column in columns)))
    return query


def list_mk(db, user, offset, limit, q):
    query = search(
        select(MataKuliah).where(MataKuliah.prodi_id == user.prodi_id),
        [MataKuliah.kode_mk, MataKuliah.nama_mk],
        q,
    )
    return list(
        db.scalars(query.order_by(MataKuliah.kode_mk, MataKuliah.id).offset(offset).limit(limit))
    )


def create_mk(db, user, payload):
    with transaction(db):
        row = MataKuliah(prodi_id=user.prodi_id, **payload.model_dump())
        db.add(row)
        db.flush()
        audit(db, user, "create", row, after=snapshot(row))
    return row


def update_mk(db, user, entity_id, payload):
    with transaction(db):
        row = owned(db, MataKuliah, entity_id, user, lock=True)
        before = snapshot(row)
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("kode_mk", row.kode_mk) != row.kode_mk and db.scalar(
            select(KurikulumMK.id).where(KurikulumMK.mk_id == row.id).limit(1)
        ):
            conflict("Kode MK yang sudah digunakan tidak dapat diganti")
        for key, value in changes.items():
            setattr(row, key, value)
        audit(db, user, "update", row, before, snapshot(row))
    return row


def delete_mk(db, user, entity_id):
    with transaction(db):
        row = owned(db, MataKuliah, entity_id, user, lock=True)
        if db.scalar(select(KurikulumMK.id).where(KurikulumMK.mk_id == row.id).limit(1)):
            conflict("MK sudah digunakan; nonaktifkan melalui PATCH")
        audit(db, user, "delete", row, snapshot(row))
        db.delete(row)


def list_curricula(db, user, offset, limit, q, status):
    query = search(
        select(Kurikulum).where(Kurikulum.prodi_id == user.prodi_id),
        [Kurikulum.kode_kurikulum, Kurikulum.nama],
        q,
    )
    if status:
        query = query.where(Kurikulum.status == status)
    return list(
        db.scalars(
            query.order_by(Kurikulum.kode_kurikulum, Kurikulum.id).offset(offset).limit(limit)
        )
    )


def create_curriculum(db, user, payload):
    with transaction(db):
        row = Kurikulum(prodi_id=user.prodi_id, status="Draft", **payload.model_dump())
        db.add(row)
        db.flush()
        audit(db, user, "create", row, after=snapshot(row))
    return row


def update_curriculum(db, user, entity_id, payload):
    with transaction(db):
        row = curriculum(db, user, entity_id, edit=True)
        before = snapshot(row)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        audit(db, user, "update", row, before, snapshot(row))
    return row


def delete_curriculum(db, user, entity_id):
    with transaction(db):
        row = curriculum(db, user, entity_id, edit=True)
        mk_ids = select(KurikulumMK.id).where(KurikulumMK.kurikulum_id == row.id)
        if (
            db.scalar(select(Angkatan.id).where(Angkatan.kurikulum_id == row.id).limit(1))
            or db.scalar(
                select(RancanganPenilaian.id)
                .where(RancanganPenilaian.kurikulum_mk_id.in_(mk_ids))
                .limit(1)
            )
            or db.scalar(select(KelasMK.id).where(KelasMK.kurikulum_mk_id.in_(mk_ids)).limit(1))
        ):
            conflict("Kurikulum sudah direferensikan; tidak dapat dihapus")
        audit(db, user, "delete", row, snapshot(row))
        db.execute(delete(MKCPL).where(MKCPL.kurikulum_mk_id.in_(mk_ids)))
        db.execute(delete(KurikulumMK).where(KurikulumMK.kurikulum_id == row.id))
        db.execute(delete(MasterCPL).where(MasterCPL.kurikulum_id == row.id))
        db.delete(row)


def list_children(db, user, curriculum_id, model, offset, limit, q, semester=None):
    curriculum(db, user, curriculum_id)
    query = select(model).where(model.kurikulum_id == curriculum_id)
    if model is KurikulumMK:
        query = search(query, [model.nama_mk], q)
        if semester is not None:
            query = query.where(model.semester == semester)
        query = query.order_by(model.semester, model.nama_mk, model.id)
    else:
        query = search(query, [model.kode_cpl, model.deskripsi], q).order_by(
            model.kode_cpl, model.id
        )
    return list(db.scalars(query.offset(offset).limit(limit)))


def create_paket(db, user, curriculum_id, payload):
    with transaction(db):
        curriculum(db, user, curriculum_id, edit=True)
        master = owned(db, MataKuliah, payload.mk_id, user, lock=True)
        if not master.aktif:
            conflict("MK nonaktif tidak dapat ditambahkan ke paket baru")
        row = KurikulumMK(kurikulum_id=curriculum_id, **payload.model_dump())
        db.add(row)
        db.flush()
        audit(db, user, "create", row, after=snapshot(row))
    return row


def used_paket(db, entity_id):
    return db.scalar(
        select(RancanganPenilaian.id)
        .where(RancanganPenilaian.kurikulum_mk_id == entity_id)
        .limit(1)
    ) or db.scalar(select(KelasMK.id).where(KelasMK.kurikulum_mk_id == entity_id).limit(1))


def update_paket(db, user, curriculum_id, entity_id, payload):
    with transaction(db):
        curriculum(db, user, curriculum_id, edit=True)
        row = child(db, KurikulumMK, entity_id, curriculum_id)
        if used_paket(db, entity_id):
            conflict("MK paket sudah digunakan oleh perkuliahan")
        before = snapshot(row)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        audit(db, user, "update", row, before, snapshot(row))
    return row


def delete_paket(db, user, curriculum_id, entity_id):
    with transaction(db):
        curriculum(db, user, curriculum_id, edit=True)
        row = child(db, KurikulumMK, entity_id, curriculum_id)
        if used_paket(db, entity_id):
            conflict("MK paket sudah digunakan oleh perkuliahan")
        audit(db, user, "delete", row, snapshot(row))
        db.delete(row)


def cpl_values(user, payload, existing=None):
    changes = payload.model_dump(exclude_unset=existing is not None)
    nasional = changes.pop("nasional", existing.prodi_id is None if existing else False)
    kategori = changes.get("kategori", existing.kategori if existing else None)
    if nasional and kategori not in ("S", "KU"):
        conflict("CPL nasional hanya boleh kategori S/KU")
    return {**changes, "prodi_id": None if nasional else user.prodi_id}


def create_cpl(db, user, curriculum_id, payload):
    with transaction(db):
        curriculum(db, user, curriculum_id, edit=True)
        row = MasterCPL(kurikulum_id=curriculum_id, **cpl_values(user, payload))
        db.add(row)
        db.flush()
        audit(db, user, "create", row, after=snapshot(row))
    return row


def update_cpl(db, user, curriculum_id, entity_id, payload):
    with transaction(db):
        curriculum(db, user, curriculum_id, edit=True)
        row = child(db, MasterCPL, entity_id, curriculum_id)
        before = snapshot(row)
        for key, value in cpl_values(user, payload, row).items():
            setattr(row, key, value)
        audit(db, user, "update", row, before, snapshot(row))
    return row


def delete_cpl(db, user, curriculum_id, entity_id):
    with transaction(db):
        curriculum(db, user, curriculum_id, edit=True)
        row = child(db, MasterCPL, entity_id, curriculum_id)
        audit(db, user, "delete", row, snapshot(row))
        # RESTRICT rejects mapped/used CPL; caller must unlink unused mappings explicitly.
        db.delete(row)


def get_matrix(db, user, curriculum_id, entity_id):
    curriculum(db, user, curriculum_id)
    child(db, KurikulumMK, entity_id, curriculum_id)
    return list(
        db.scalars(select(MKCPL).where(MKCPL.kurikulum_mk_id == entity_id).order_by(MKCPL.cpl_id))
    )


def replace_matrix(db, user, curriculum_id, entity_id, payload):
    with transaction(db):
        curriculum(db, user, curriculum_id, edit=True)
        row = child(db, KurikulumMK, entity_id, curriculum_id)
        requested = {item.cpl_id: item for item in payload.items}
        for cpl_id in sorted(requested):
            child(db, MasterCPL, cpl_id, curriculum_id)
        current = {
            link.cpl_id: link
            for link in db.scalars(select(MKCPL).where(MKCPL.kurikulum_mk_id == entity_id))
        }
        removed = current.keys() - requested.keys()
        if removed and db.scalar(
            select(CPMKCPL.cpl_id)
            .join(CPMK, CPMKCPL.cpmk_id == CPMK.id)
            .join(RancanganPenilaian, CPMK.rancangan_id == RancanganPenilaian.id)
            .where(RancanganPenilaian.kurikulum_mk_id == entity_id, CPMKCPL.cpl_id.in_(removed))
            .limit(1)
        ):
            conflict("Pembebanan CPL masih dipakai CPMK")
        before = {"items": [snapshot(link) for link in current.values()]}
        for cpl_id in removed:
            db.delete(current[cpl_id])
        for cpl_id, item in requested.items():
            if cpl_id in current:
                current[cpl_id].urutan_rps = item.urutan_rps
            else:
                db.add(MKCPL(kurikulum_mk_id=entity_id, **item.model_dump()))
        audit(
            db,
            user,
            "replace_matrix",
            row,
            before,
            {"items": [item.model_dump(mode="json") for item in payload.items]},
        )
    return get_matrix(db, user, curriculum_id, entity_id)


def transition(db, user, curriculum_id, target):
    with transaction(db):
        row = curriculum(db, user, curriculum_id, lock=True)
        expected = "Draft" if target == "Aktif" else "Aktif"
        if row.status != expected:
            conflict(f"Transisi hanya {expected} menjadi {target}")
        if target == "Aktif":
            for cpl in db.scalars(select(MasterCPL).where(MasterCPL.kurikulum_id == row.id)):
                if cpl.prodi_id is not None and cpl.prodi_id != user.prodi_id:
                    conflict("CPL harus berasal dari prodi kurikulum")
            paket = list(db.scalars(select(KurikulumMK).where(KurikulumMK.kurikulum_id == row.id)))
            if not paket:
                conflict("Kurikulum harus memiliki minimal satu MK paket")
            for mk in paket:
                master = db.get(MataKuliah, mk.mk_id)
                if master.prodi_id != user.prodi_id or not 1 <= mk.semester <= 8 or mk.sks <= 0:
                    conflict("Konteks atau isi MK paket tidak valid")
                links = list(db.scalars(select(MKCPL).where(MKCPL.kurikulum_mk_id == mk.id)))
                if not links:
                    conflict("Setiap MK paket wajib memiliki pembebanan CPL")
                for link in links:
                    cpl = db.get(MasterCPL, link.cpl_id)
                    if cpl.kurikulum_id != row.id or (
                        cpl.prodi_id is not None and cpl.prodi_id != user.prodi_id
                    ):
                        conflict("CPL harus berasal dari kurikulum dan prodi yang sama")
        before = snapshot(row)
        row.status = target
        audit(db, user, "activate" if target == "Aktif" else "archive", row, before, snapshot(row))
    return row


def clone(db, user, curriculum_id, payload):
    with transaction(db):
        source = curriculum(db, user, curriculum_id, lock=True)
        target = Kurikulum(prodi_id=user.prodi_id, status="Draft", **payload.model_dump())
        db.add(target)
        db.flush()
        cpl_map = {}
        for cpl in db.scalars(
            select(MasterCPL).where(MasterCPL.kurikulum_id == source.id).order_by(MasterCPL.id)
        ):
            if cpl.prodi_id is not None and cpl.prodi_id != user.prodi_id:
                conflict("CPL sumber berasal dari prodi berbeda")
            values = {attr.key: getattr(cpl, attr.key) for attr in inspect(cpl).mapper.column_attrs}
            values.pop("id")
            values["kurikulum_id"] = target.id
            copy = MasterCPL(**values)
            db.add(copy)
            db.flush()
            cpl_map[cpl.id] = copy.id
        for mk in db.scalars(
            select(KurikulumMK)
            .where(KurikulumMK.kurikulum_id == source.id)
            .order_by(KurikulumMK.id)
        ):
            owned(db, MataKuliah, mk.mk_id, user)
            values = {attr.key: getattr(mk, attr.key) for attr in inspect(mk).mapper.column_attrs}
            values.pop("id")
            values["kurikulum_id"] = target.id
            copy = KurikulumMK(**values)
            db.add(copy)
            db.flush()
            for link in db.scalars(select(MKCPL).where(MKCPL.kurikulum_mk_id == mk.id)):
                if link.cpl_id not in cpl_map:
                    conflict("Sumber memiliki pemetaan lintas versi yang tidak valid")
                db.add(
                    MKCPL(
                        kurikulum_mk_id=copy.id,
                        cpl_id=cpl_map[link.cpl_id],
                        urutan_rps=link.urutan_rps,
                    )
                )
        audit(db, user, "clone", target, {"sumber_kurikulum_id": str(source.id)}, snapshot(target))
    return target
