from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    CPMK,
    CPMKCPL,
    MKCPL,
    AuditLog,
    InstrumenPenilaian,
    KelasMK,
    Kurikulum,
    KurikulumMK,
    MahasiswaPeriode,
    MasterCPL,
    MataKuliah,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    RancanganPenilaian,
    SubCPMK,
    User,
)
from app.schemas.grading import GradeBatch
from app.services import academic, grading


def auth(dataset, settings, role="dosen"):
    return {"Authorization": "Bearer " + create_access_token(dataset[role], settings)}


def grade_item(dataset, score="80", *, instrument=None, student=None):
    return dict(
        instrumen_id=str(instrument or dataset["instrument"].id),
        mahasiswa_id=str(student or dataset["mahasiswa"].id),
        nilai_mentah=score,
    )


def save(client, dataset, settings, items=None, *, course=None, role="dosen"):
    return client.put(
        f"/api/v1/kelas-mk/{course or dataset['course_a'].id}/nilai",
        json={"items": items or [grade_item(dataset)]},
        headers=auth(dataset, settings, role),
    )


def attain(client, dataset, settings, *, role="dosen", course=None):
    response = client.get(
        f"/api/v1/kelas-mk/{course or dataset['course_a'].id}/capaian",
        headers=auth(dataset, settings, role),
    )
    assert response.status_code == 200, response.text
    return response.json()


def metric(results, kind):
    return next(r for r in results if r["jenis"] == kind)


def enroll_other(db, dataset, course=None):
    course = course or dataset["course_a"]
    db.add(
        MahasiswaPeriode(
            mahasiswa_id=dataset["other_student"].id,
            periode_id=dataset["period"].id,
            kelas_periode_id=course.kelas_periode_id,
            status="Aktif",
        )
    )
    db.add(
        PesertaKelasMK(
            kelas_mk_id=course.id, mahasiswa_id=dataset["other_student"].id, mk_id=dataset["mk"].id
        )
    )
    db.commit()


def test_bulk_upsert_idempotent_and_precise_audit(client, dataset, settings, db):
    first = save(client, dataset, settings, [grade_item(dataset, "0")])
    assert first.status_code == 200, first.text
    row = first.json()[0]
    assert row["nilai_mentah"] == "0.00"
    same = save(client, dataset, settings, [grade_item(dataset, "0")]).json()[0]
    assert same == row
    changed = save(client, dataset, settings, [grade_item(dataset, "99.99")]).json()[0]
    assert changed["id"] == row["id"]
    assert changed["diubah_oleh"] == str(dataset["dosen"].id)
    audits = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.entitas == "nilai_mahasiswa")
            .order_by(AuditLog.waktu, AuditLog.id)
        )
    )
    assert len(audits) == 2
    update = next(a for a in audits if a.aksi == "update")
    assert update.sebelum["nilai_mentah"] == "0.00"
    assert update.sesudah["nilai_mentah"] == "99.99"
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 1


def test_payload_duplicates_bounds_and_nonfinite_rejected(client, dataset, settings, db):
    item = grade_item(dataset)
    assert save(client, dataset, settings, [item, item]).status_code == 422
    for score in ["-0.01", "100.01", "12.345", "NaN", "Infinity", None, True]:
        assert save(client, dataset, settings, [grade_item(dataset, score)]).status_code == 422
    assert (
        client.put(
            f"/api/v1/kelas-mk/{dataset['course_a'].id}/nilai",
            json={"items": []},
            headers=auth(dataset, settings),
        ).status_code
        == 422
    )
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 0


def test_whole_batch_rollback_unknown_instrument_or_student(client, dataset, settings, db):
    for invalid in [
        grade_item(dataset, instrument=uuid4()),
        grade_item(dataset, student=dataset["other_student"].id),
    ]:
        assert save(client, dataset, settings, [grade_item(dataset), invalid]).status_code == 404
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 0
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_roles_assignment_and_student_privacy(client, dataset, settings, db):
    enroll_other(db, dataset)
    assert save(client, dataset, settings, role="admin").status_code == 403
    assert save(client, dataset, settings, role="mahasiswa").status_code == 403
    assert save(client, dataset, settings, role="outsider").status_code == 404
    assert (
        save(
            client,
            dataset,
            settings,
            [grade_item(dataset), grade_item(dataset, "20", student=dataset["other_student"].id)],
        ).status_code
        == 200
    )
    url = f"/api/v1/kelas-mk/{dataset['course_a'].id}"
    for suffix in ["/nilai", "/capaian"]:
        assert (
            client.get(url + suffix, headers=auth(dataset, settings, "outsider")).status_code == 404
        )
    own = client.get(url + "/nilai", headers=auth(dataset, settings, "mahasiswa")).json()
    assert len(own) == 1 and own[0]["mahasiswa_id"] == str(dataset["mahasiswa"].id)
    result = attain(client, dataset, settings, role="mahasiswa")
    assert len(result["peserta"]) == 1 and result["rekap"] == []
    assert result["peserta"][0]["mahasiswa_id"] == str(dataset["mahasiswa"].id)
    assert (
        client.get(
            f"/api/v1/kelas-mk/{dataset['course_b'].id}/nilai",
            headers=auth(dataset, settings, "mahasiswa"),
        ).status_code
        == 404
    )


@pytest.mark.parametrize("invalid", ["weight", "mapping", "roster", "account"])
def test_grade_requires_readiness_active_roster_and_account(client, dataset, settings, db, invalid):
    if invalid == "weight":
        dataset["instrument"].bobot_persentase = 99
    elif invalid == "mapping":
        db.delete(db.scalar(select(CPMKCPL)))
    elif invalid == "roster":
        db.scalar(select(MahasiswaPeriode)).status = "Cuti"
    else:
        dataset["mahasiswa"].aktif = False
    db.commit()
    assert save(client, dataset, settings).status_code == (
        409 if invalid in ["weight", "mapping"] else 404
    )
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 0


def test_missing_zero_and_unready_are_distinct(client, dataset, settings, db):
    empty = metric(attain(client, dataset, settings)["rekap"], "CPMK")
    assert empty["capaian"] is None and empty["status"] == "Belum lengkap"
    dataset["instrument"].bobot_persentase = 90
    db.commit()
    assert (
        metric(attain(client, dataset, settings)["rekap"], "CPMK")["status"] == "Belum siap dinilai"
    )
    dataset["instrument"].bobot_persentase = 100
    db.commit()
    assert save(client, dataset, settings, [grade_item(dataset, "0")]).status_code == 200
    zero = metric(attain(client, dataset, settings)["rekap"], "CPMK")
    assert zero["capaian"] == "0.00" and zero["mahasiswa_lengkap"] == 1
    # One grade freezes shared structure in B as well, while grade correction remains allowed.
    base = f"/api/v1/rancangan-penilaian/{dataset['design'].id}"
    assert (
        client.post(
            base + "/cpmk",
            json={"kode_cpmk": "NO", "deskripsi": "Frozen"},
            headers=auth(dataset, settings),
        ).status_code
        == 409
    )
    assert save(client, dataset, settings).status_code == 200


def test_class_average_counts_only_complete_and_keeps_shared_classes_separate(
    client, dataset, settings, db
):
    enroll_other(db, dataset, dataset["course_b"])
    assert save(client, dataset, settings, [grade_item(dataset, "80")]).status_code == 200
    assert (
        save(
            client,
            dataset,
            settings,
            [grade_item(dataset, "20", student=dataset["other_student"].id)],
            course=dataset["course_b"].id,
        ).status_code
        == 200
    )
    assert metric(attain(client, dataset, settings)["rekap"], "CPL")["capaian"] == "80.00"
    assert (
        metric(attain(client, dataset, settings, course=dataset["course_b"].id)["rekap"], "CPL")[
            "capaian"
        ]
        == "20.00"
    )


def test_incomplete_students_excluded_from_mean(client, dataset, settings, db):
    enroll_other(db, dataset)
    save(client, dataset, settings)
    average = metric(attain(client, dataset, settings)["rekap"], "CPMK")
    assert (average["capaian"], average["mahasiswa_lengkap"], average["total_mahasiswa"]) == (
        "80.00",
        1,
        2,
    )
    assert average["status"] == "Belum lengkap"


def test_close_reopen_preserves_values_and_structure_freeze(client, dataset, settings, db):
    url = f"/api/v1/periode-akademik/{dataset['period'].id}"
    for role in ["dosen", "mahasiswa"]:
        assert client.post(url + "/tutup", headers=auth(dataset, settings, role)).status_code == 403
    # Incomplete grades do not prevent closing.
    closed = client.post(url + "/tutup", headers=auth(dataset, settings, "admin"))
    assert closed.status_code == 200 and closed.json()["ditutup_pada"] is not None
    assert closed.json()["ditutup_oleh"] == str(dataset["admin"].id)
    assert save(client, dataset, settings).status_code == 409
    assert metric(attain(client, dataset, settings)["rekap"], "CPMK")["capaian"] is None
    for payload in [{}, {"alasan": "  "}]:
        assert (
            client.post(
                url + "/buka-kembali", json=payload, headers=auth(dataset, settings, "admin")
            ).status_code
            == 422
        )
    assert (
        client.post(
            url + "/buka-kembali",
            json={"alasan": " Koreksi nilai "},
            headers=auth(dataset, settings, "admin"),
        ).status_code
        == 200
    )
    assert save(client, dataset, settings).status_code == 200
    assert client.post(url + "/tutup", headers=auth(dataset, settings, "admin")).status_code == 200
    assert (
        client.post(
            url + "/buka-kembali",
            json={"alasan": "Lengkapi"},
            headers=auth(dataset, settings, "admin"),
        ).status_code
        == 200
    )
    assert save(client, dataset, settings, [grade_item(dataset, "90")]).status_code == 200
    assert (
        client.post(
            f"/api/v1/rancangan-penilaian/{dataset['design'].id}/cpmk",
            json={"kode_cpmk": "NO", "deskripsi": "Frozen"},
            headers=auth(dataset, settings),
        ).status_code
        == 409
    )
    audits = list(db.scalars(select(AuditLog).where(AuditLog.aksi == "reopen")))
    assert len(audits) == 2 and {a.alasan for a in audits} == {"Koreksi nilai", "Lengkapi"}
    assert all(a.sebelum["status"] == "Ditutup" and a.sesudah["status"] == "Dibuka" for a in audits)


def test_audit_failure_rolls_back_entire_grade_batch(client, dataset, settings, db, monkeypatch):
    def fail(*args, **kwargs):
        raise IntegrityError("Audit unavailable", None, Exception())

    monkeypatch.setattr(academic, "record", fail)
    assert save(client, dataset, settings).status_code == 409
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 0


def test_period_audit_failure_rolls_back_transition(client, dataset, settings, db):
    def fail(session, *args):
        if any(isinstance(row, AuditLog) and row.aksi == "close" for row in session.new):
            raise IntegrityError("Audit unavailable", None, Exception())

    event.listen(Session, "before_flush", fail)
    try:
        response = client.post(
            f"/api/v1/periode-akademik/{dataset['period'].id}/tutup",
            headers=auth(dataset, settings, "admin"),
        )
        assert response.status_code == 409
    finally:
        event.remove(Session, "before_flush", fail)
    db.expire_all()
    assert db.get(PeriodeAkademik, dataset["period"].id).status == "Dibuka"
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_existing_foreign_instrument_rejected_atomically(client, dataset, settings, db):
    _, instrument = add_course(db, dataset)
    assert (
        save(
            client,
            dataset,
            settings,
            [grade_item(dataset), grade_item(dataset, instrument=instrument.id)],
        ).status_code
        == 404
    )
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 0


def test_class_average_rounds_only_final_result_and_cpl_contributes_fully(
    client, dataset, settings, db
):
    enroll_other(db, dataset)
    first = dataset["instrument"]
    first.bobot_persentase = 40
    second = InstrumenPenilaian(
        sub_cpmk_id=first.sub_cpmk_id,
        nama_instrumen="Second",
        jenis_instrumen="UTS",
        bobot_persentase=60,
    )
    cpl = MasterCPL(
        kurikulum_id=dataset["angkatan"].kurikulum_id,
        prodi_id=dataset["prodi"].id,
        kode_cpl="CPL-02",
        kategori="P",
        deskripsi="Second CPL",
    )
    db.add_all([second, cpl])
    db.flush()
    db.add(MKCPL(kurikulum_mk_id=dataset["kurikulum_mk"].id, cpl_id=cpl.id))
    sub = db.get(SubCPMK, first.sub_cpmk_id)
    db.add(CPMKCPL(cpmk_id=sub.cpmk_id, cpl_id=cpl.id))
    db.commit()
    assert (
        save(
            client,
            dataset,
            settings,
            [
                grade_item(dataset, "0"),
                grade_item(dataset, "0.01", instrument=second.id),
                grade_item(dataset, "0.01", student=dataset["other_student"].id),
                grade_item(
                    dataset, "0.02", student=dataset["other_student"].id, instrument=second.id
                ),
            ],
        ).status_code
        == 200
    )
    result = attain(client, dataset, settings)
    # Raw 0.006 and 0.016 average 0.011 => 0.01; averaging displays yields 0.02.
    assert metric(result["rekap"], "CPMK")["capaian"] == "0.01"
    for cpl_result in [r for r in result["peserta"][0]["hasil"] if r["jenis"] == "CPL"]:
        assert cpl_result["total_instrumen"] == 2
    # Both CPLs receive the entire contribution, without splitting scores between CPLs.
    assert len({r["capaian"] for r in result["rekap"] if r["jenis"] == "CPL"}) == 1


def test_close_blocks_waiting_grade_and_rechecks_assignment(dataset, engine, db, monkeypatch):
    """A writer already authorized before waiting must observe closure/reassignment."""
    for change in ["close", "reassign"]:
        entered = Event()
        original = grading.require_class_access
        calls = []

        def observed(*args, original=original, calls=calls, entered=entered, **kwargs):
            row = original(*args, **kwargs)
            calls.append(1)
            if len(calls) == 1:
                entered.set()
            return row

        monkeypatch.setattr(grading, "require_class_access", observed)

        def worker():
            with Session(engine, expire_on_commit=False) as session:
                try:
                    grading.save_grades(
                        session,
                        session.get(User, dataset["dosen"].id),
                        dataset["course_a"].id,
                        GradeBatch(items=[grade_item(dataset)]),
                    )
                except HTTPException as exc:
                    return exc.status_code
                return 200

        # Hold the same row lock used by the close service while the writer discovers its class.
        with Session(engine, expire_on_commit=False) as blocker:
            period = blocker.scalar(
                select(PeriodeAkademik)
                .where(PeriodeAkademik.id == dataset["period"].id)
                .with_for_update()
            )
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(worker)
                try:
                    assert entered.wait(5)
                    if change == "close":
                        grading.transition_period(
                            blocker, blocker.get(User, dataset["admin"].id), period.id
                        )
                    else:
                        design = RancanganPenilaian(
                            periode_id=period.id,
                            kurikulum_mk_id=dataset["kurikulum_mk"].id,
                            dosen_id=dataset["outsider"].id,
                        )
                        blocker.add(design)
                        blocker.flush()
                        blocker.get(KelasMK, dataset["course_a"].id).rancangan_id = design.id
                        blocker.commit()
                finally:
                    blocker.rollback()
                assert future.result(timeout=8) == (409 if change == "close" else 404)
        monkeypatch.setattr(grading, "require_class_access", original)
        db.expire_all()
        db.get(PeriodeAkademik, dataset["period"].id).status = "Dibuka"
        db.commit()
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 0


def add_course(db, dataset, *, weight=100, period=None, curriculum=None, code="SECOND"):
    """A distinct master MK avoids the forbidden repeated-course enrollment."""
    curriculum = curriculum or dataset["angkatan"].kurikulum_id
    period = period or dataset["period"]
    master = MataKuliah(prodi_id=dataset["prodi"].id, kode_mk=code, nama_mk=code)
    db.add(master)
    db.flush()
    mk = KurikulumMK(kurikulum_id=curriculum, mk_id=master.id, nama_mk=code, sks=6, semester=1)
    db.add(mk)
    db.flush()
    cpl = db.scalar(select(MasterCPL).where(MasterCPL.kurikulum_id == curriculum))
    if cpl is None:
        cpl = MasterCPL(
            kurikulum_id=curriculum,
            prodi_id=dataset["prodi"].id,
            kode_cpl="CPL-01",
            kategori="P",
            deskripsi="Separate version",
        )
        db.add(cpl)
        db.flush()
    db.add(MKCPL(kurikulum_mk_id=mk.id, cpl_id=cpl.id))
    design = RancanganPenilaian(
        periode_id=period.id, kurikulum_mk_id=mk.id, dosen_id=dataset["dosen"].id
    )
    db.add(design)
    db.flush()
    from app.models import KelasPeriode

    klass = db.scalar(
        select(KelasPeriode).where(KelasPeriode.id == dataset["course_a"].kelas_periode_id)
    )
    if period.id != dataset["period"].id:
        klass = KelasPeriode(
            periode_id=period.id,
            angkatan_id=dataset["angkatan"].id,
            kode_kelas="A",
            semester_studi=3,
        )
        db.add(klass)
        db.flush()
    course = KelasMK(kelas_periode_id=klass.id, kurikulum_mk_id=mk.id, rancangan_id=design.id)
    cpmk = CPMK(rancangan_id=design.id, kode_cpmk="CPMK-1", deskripsi="Second")
    db.add_all([course, cpmk])
    db.flush()
    db.add(CPMKCPL(cpmk_id=cpmk.id, cpl_id=cpl.id))
    sub = SubCPMK(cpmk_id=cpmk.id, kode_sub="S", deskripsi="Second sub")
    db.add(sub)
    db.flush()
    instrument = InstrumenPenilaian(
        sub_cpmk_id=sub.id, nama_instrumen="Exam", jenis_instrumen="UAS", bobot_persentase=weight
    )
    db.add(instrument)
    db.add(
        PesertaKelasMK(kelas_mk_id=course.id, mahasiswa_id=dataset["mahasiswa"].id, mk_id=master.id)
    )
    db.commit()
    return course, instrument


def personal(client, dataset, settings, period=None, cumulative=False):
    response = client.get(
        "/api/v1/capaian/saya",
        params={"periode_id": str(period or dataset["period"].id), "kumulatif": cumulative},
        headers=auth(dataset, settings, "mahasiswa"),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_decimal_weighted_sub_cpmk_cpl_no_simple_average(client, dataset, settings, db):
    first = dataset["instrument"]
    first.bobot_persentase = Decimal("20")
    sub = db.get(SubCPMK, first.sub_cpmk_id)
    second = InstrumenPenilaian(
        sub_cpmk_id=sub.id, nama_instrumen="30", jenis_instrumen="UTS", bobot_persentase=30
    )
    cpl = db.scalar(select(MasterCPL))
    c2 = CPMK(rancangan_id=dataset["design"].id, kode_cpmk="C2", deskripsi="Other CPMK")
    db.add_all([second, c2])
    db.flush()
    db.add(CPMKCPL(cpmk_id=c2.id, cpl_id=cpl.id))
    s2 = SubCPMK(cpmk_id=c2.id, kode_sub="S2", deskripsi="Other sub")
    db.add(s2)
    db.flush()
    third = InstrumenPenilaian(
        sub_cpmk_id=s2.id, nama_instrumen="50", jenis_instrumen="UAS", bobot_persentase=50
    )
    db.add(third)
    db.commit()
    assert (
        save(
            client,
            dataset,
            settings,
            [grade_item(dataset, "80"), grade_item(dataset, "60", instrument=second.id)],
        ).status_code
        == 200
    )
    result = attain(client, dataset, settings)["peserta"][0]["hasil"]
    assert metric(result, "Mata kuliah")["capaian"] is None
    cp = next(r for r in result if r["jenis"] == "CPMK" and r["kode"] == "CPMK-1")
    assert cp["capaian"] == "68.00"
    assert (
        save(
            client, dataset, settings, [grade_item(dataset, "100", instrument=third.id)]
        ).status_code
        == 200
    )
    cpl_result = personal(client, dataset, settings)["hasil"][0]
    assert cpl_result["capaian"] == "84.00" and cpl_result["total_instrumen"] == 3


def test_personal_cpl_merges_enrolled_mk_no_sks_weight_and_requires_all_scores(
    client, dataset, settings, db
):
    course, instrument = add_course(db, dataset)
    save(client, dataset, settings, [grade_item(dataset, "80")])
    assert personal(client, dataset, settings)["hasil"][0]["capaian"] is None
    save(
        client,
        dataset,
        settings,
        [grade_item(dataset, "60", instrument=instrument.id)],
        course=course.id,
    )
    result = personal(client, dataset, settings)["hasil"][0]
    assert result["capaian"] == "70.00" and result["total_instrumen"] == 2
    # Another class enrollment was never selected; only packages followed by this JWT student count.
    assert set(personal(client, dataset, settings)["kelas_mk_ids"]) == {
        str(course.id),
        str(dataset["course_a"].id),
    }


def test_cumulative_cutoff_and_version_isolation(client, dataset, settings, db):
    save(client, dataset, settings)
    period = PeriodeAkademik(prodi_id=dataset["prodi"].id, tahun_mulai=2026, semester="Genap")
    db.add(period)
    db.commit()
    add_course(db, dataset, period=period, code="FUTURE")
    assert personal(client, dataset, settings, cumulative=True)["hasil"][0]["capaian"] == "80.00"
    assert (
        personal(client, dataset, settings, period=period.id, cumulative=True)["hasil"][0][
            "capaian"
        ]
        is None
    )
    assert personal(client, dataset, settings, period=period.id)["hasil"][0]["total_instrumen"] == 1
    kur = Kurikulum(prodi_id=dataset["prodi"].id, kode_kurikulum="OTHER", nama="Other")
    db.add(kur)
    db.commit()
    add_course(db, dataset, curriculum=kur.id, code="VERSION")
    # Historical reports still distinguish identical CPL codes by curriculum/UUID.
    results = personal(client, dataset, settings)["hasil"]
    assert len(results) == 2 and len({r["kurikulum_id"] for r in results}) == 2
    assert {r["kode"] for r in results} == {"CPL-01"}
    assert sorted(r["total_instrumen"] for r in results) == [1, 1]


def test_unassessed_nodes_and_unready_cpl_across_mk(client, dataset, settings, db):
    cpl = db.scalar(select(MasterCPL))
    cpmk = CPMK(
        rancangan_id=dataset["design"].id, kode_cpmk="UNASSESSED", deskripsi="No instruments"
    )
    db.add(cpmk)
    db.flush()
    db.add(CPMKCPL(cpmk_id=cpmk.id, cpl_id=cpl.id))
    db.commit()
    save(client, dataset, settings)
    result = attain(client, dataset, settings)["peserta"][0]["hasil"]
    empty = next(r for r in result if r["kode"] == "UNASSESSED")
    assert empty["capaian"] is None and empty["total_instrumen"] == 0
    add_course(db, dataset, weight=99)
    assert personal(client, dataset, settings)["hasil"][0]["status"] == "Belum siap dinilai"
