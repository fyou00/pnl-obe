from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    Angkatan,
    AuditLog,
    KelasMK,
    Kurikulum,
    Mahasiswa,
    MahasiswaPeriode,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    Prodi,
    RancanganPenilaian,
    User,
)
from app.schemas.academic_admin import RosterPatch
from app.services import academic as service
from app.services.seed import ensure_user


@pytest.fixture
def admin_client(client, dataset, settings):
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["admin"], settings)
    return client


def post(client, path, payload):
    response = client.post("/api/v1" + path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def new_period(client, year=2028, semester="Ganjil"):
    return post(client, "/periode-akademik", {"tahun_mulai": year, "semester": semester})


def new_class(client, period_id, cohort_id, code="A", semester=5):
    return post(
        client,
        f"/periode-akademik/{period_id}/kelas",
        {"angkatan_id": str(cohort_id), "kode_kelas": code, "semester_studi": semester},
    )


def test_angkatan_crud_curriculum_state_and_freeze(admin_client, dataset, db):
    client = admin_client
    curriculum_id = str(dataset["angkatan"].kurikulum_id)
    payload = {"tahun_masuk": 2024, "kurikulum_id": curriculum_id}
    assert client.post("/api/v1/angkatan", json=payload).status_code == 409  # Draft
    assert client.post(f"/api/v1/kurikulum/{curriculum_id}/aktifkan").status_code == 200
    row = post(client, "/angkatan", payload)
    path = "/api/v1/angkatan/" + row["id"]
    assert client.get(path).json()["tahun_masuk"] == 2024
    assert len(client.get("/api/v1/angkatan?tahun_masuk=2024").json()) == 1
    assert client.post("/api/v1/angkatan", json=payload).status_code == 409
    assert client.patch(path, json={"tahun_masuk": 2023}).json()["tahun_masuk"] == 2023
    copy = post(
        client, f"/kurikulum/{curriculum_id}/salin", {"kode_kurikulum": "NEXT", "nama": "Next"}
    )
    assert client.post(f"/api/v1/kurikulum/{copy['id']}/aktifkan").status_code == 200
    assert client.patch(path, json={"kurikulum_id": copy["id"]}).status_code == 200
    existing = "/api/v1/angkatan/" + str(dataset["angkatan"].id)
    assert client.patch(existing, json={"kurikulum_id": copy["id"]}).status_code == 409
    assert client.patch(existing, json={"tahun_masuk": 2025}).status_code == 409
    assert client.delete(existing).status_code == 409
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404
    assert client.post(f"/api/v1/kurikulum/{copy['id']}/arsipkan").status_code == 200
    assert (
        client.post(
            "/api/v1/angkatan", json={"tahun_masuk": 2022, "kurikulum_id": copy["id"]}
        ).status_code
        == 409
    )
    audit = list(
        db.scalars(
            select(AuditLog).where(AuditLog.entitas_id == UUID(row["id"])).order_by(AuditLog.waktu)
        )
    )
    assert audit[0].aksi == "create" and audit[-1].aksi == "delete"


def test_period_crud_and_identity_protection(admin_client, dataset):
    client = admin_client
    period = new_period(client)
    base = "/api/v1/periode-akademik/" + period["id"]
    assert period["tahun_akademik"] == "2028/2029" and period["status"] == "Dibuka"
    assert client.get(base).status_code == 200
    assert (
        client.post(
            "/api/v1/periode-akademik", json={"tahun_mulai": 2028, "semester": "Ganjil"}
        ).status_code
        == 409
    )
    assert client.patch(base, json={"semester": "Genap"}).json()["semester"] == "Genap"
    assert len(client.get("/api/v1/periode-akademik?tahun_mulai=2028&semester=Genap").json()) == 1
    assert client.delete(base).status_code == 204
    assert client.get(base).status_code == 404
    used = "/api/v1/periode-akademik/" + str(dataset["period"].id)
    assert client.patch(used, json={"tahun_mulai": 2027}).status_code == 409
    assert client.patch(used, json={"semester": "Genap"}).status_code == 409
    assert client.delete(used).status_code == 409


def test_class_labels_parity_and_cohort_consistency(admin_client, dataset):
    client = admin_client
    cohort = dataset["angkatan"].id
    period = new_period(client)
    base = "/api/v1/periode-akademik/" + period["id"]
    a = new_class(client, period["id"], cohort, "C", 5)
    assert a["label"] == "TI-3C" and a["tingkat"] == 3
    assert client.get(base + "/kelas/" + a["id"]).json()["semester_studi"] == 5
    for code, semester, expected in [("D", 4, 409), ("D", 3, 409), ("K", 5, 422), ("A", None, 422)]:
        assert (
            client.post(
                base + "/kelas",
                json={"angkatan_id": str(cohort), "kode_kelas": code, "semester_studi": semester},
            ).status_code
            == expected
        )
    b = new_class(client, period["id"], cohort, "D", 5)
    k = new_class(client, period["id"], cohort, "K", None)
    assert k["label"] == "TI-K" and k["tingkat"] is None
    assert (
        client.patch(base + "/kelas/" + b["id"], json={"kode_kelas": "E"}).json()["label"]
        == "TI-3E"
    )
    assert client.delete(base + "/kelas/" + b["id"]).status_code == 204
    later = new_period(client, 2029)
    assert new_class(client, later["id"], cohort, "A", 7)["label"] == "TI-4A"
    genap = new_period(client, 2029, "Genap")
    assert new_class(client, genap["id"], cohort, "A", 8)["label"] == "TI-4A"
    assert len(client.get(base + "/kelas?angkatan_id=" + str(cohort)).json()) == 2
    before = new_period(client, 2020)
    assert (
        client.post(
            "/api/v1/periode-akademik/" + before["id"] + "/kelas",
            json={"angkatan_id": str(cohort), "kode_kelas": "A", "semester_studi": 1},
        ).status_code
        == 409
    )
    assert client.patch(base + "/kelas/" + k["id"], json={"kode_kelas": "B"}).status_code == 409


def test_link_existing_student_accounts(admin_client, dataset, db, seed_config):
    client = admin_client
    cohort = dataset["angkatan"].id
    account = ensure_user(
        db,
        dataset["prodi"],
        nama="New student",
        nim_nidn="NEW-MHS",
        email="new-mhs@example.com",
        password=seed_config.seed_mahasiswa_password,
        role="Mahasiswa",
    )
    db.commit()
    path = f"/api/v1/angkatan/{cohort}/mahasiswa"
    response = client.post(path, json={"user_id": str(account.id)})
    assert response.status_code == 201 and "password" not in response.text
    assert client.post(path, json={"user_id": str(account.id)}).status_code == 409
    assert client.post(path, json={"user_id": str(dataset["dosen"].id)}).status_code == 409
    assert str(account.id) in str(client.get(path).json())
    assert db.get(Mahasiswa, account.id).angkatan_id == cohort


def test_roster_k_status_and_period_history(admin_client, dataset, db):
    client = admin_client
    cohort, student = dataset["angkatan"].id, str(dataset["mahasiswa"].id)
    old_base = "/api/v1/periode-akademik/" + str(dataset["period"].id)
    period = new_period(client)
    a = new_class(client, period["id"], cohort)
    k = new_class(client, period["id"], cohort, "K", None)
    base = "/api/v1/periode-akademik/" + period["id"]
    body = {"mahasiswa_id": student, "kelas_periode_id": k["id"], "status": "Cuti"}
    row = post(client, base.removeprefix("/api/v1") + "/mahasiswa", body)
    path = base + "/mahasiswa/" + student
    assert row["status"] == "Cuti"
    assert client.post(base + "/mahasiswa", json=body).status_code == 409
    assert client.patch(path, json={"status": "Nonaktif"}).json()["status"] == "Nonaktif"
    assert client.patch(path, json={"status": "Aktif"}).status_code == 409
    assert (
        client.patch(path, json={"kelas_periode_id": a["id"], "status": "Aktif"}).status_code == 200
    )
    assert (
        client.get(base + "/mahasiswa?status=Aktif&kelas_periode_id=" + a["id"]).json()[0][
            "mahasiswa_id"
        ]
        == student
    )
    assert client.get(old_base + "/mahasiswa/" + student).json()["status"] == "Aktif"
    assert client.get(old_base + "/mahasiswa/" + student).json()["kelas_periode_id"] == str(
        dataset["course_a"].kelas_periode_id
    )
    assert (
        db.scalar(
            select(PesertaKelasMK.kelas_mk_id).where(PesertaKelasMK.mahasiswa_id == UUID(student))
        )
        == dataset["course_a"].id
    )
    assert (
        client.patch(
            base + "/kelas/" + a["id"], json={"kode_kelas": "K", "semester_studi": None}
        ).status_code
        == 409
    )
    assert client.delete(base + "/kelas/" + a["id"]).status_code == 409
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404
    assert client.get(old_base + "/mahasiswa/" + student).status_code == 200


def test_roster_transfer_sync_and_grade_freeze(admin_client, dataset, db):
    client = admin_client
    base = "/api/v1/periode-akademik/" + str(dataset["period"].id)
    student = dataset["mahasiswa"].id
    path = base + "/mahasiswa/" + str(student)
    b_class = dataset["course_b"].kelas_periode_id
    assert client.patch(path, json={"kelas_periode_id": str(b_class)}).status_code == 200
    db.expire_all()
    assert list(
        db.scalars(select(PesertaKelasMK.kelas_mk_id).where(PesertaKelasMK.mahasiswa_id == student))
    ) == [dataset["course_b"].id]
    assert (
        client.patch(
            path, json={"kelas_periode_id": str(dataset["course_a"].kelas_periode_id)}
        ).status_code
        == 200
    )
    k = new_class(client, str(dataset["period"].id), dataset["angkatan"].id, "K", None)
    assert (
        client.patch(path, json={"kelas_periode_id": k["id"], "status": "Cuti"}).status_code == 200
    )
    db.expire_all()
    assert (
        list(
            db.scalars(
                select(PesertaKelasMK.kelas_mk_id).where(PesertaKelasMK.mahasiswa_id == student)
            )
        )
        == []
    )
    assert (
        client.patch(
            path,
            json={"kelas_periode_id": str(dataset["course_a"].kelas_periode_id), "status": "Aktif"},
        ).status_code
        == 200
    )
    db.add(
        NilaiMahasiswa(
            instrumen_id=dataset["instrument"].id,
            kelas_mk_id=dataset["course_a"].id,
            mahasiswa_id=student,
            nilai_mentah=0,
            diubah_oleh=dataset["dosen"].id,
        )
    )
    db.commit()
    assert client.patch(path, json={"kelas_periode_id": str(b_class)}).status_code == 409
    assert client.delete(path).status_code == 409
    assert client.patch(path, json={"status": "Aktif"}).status_code == 200  # unchanged, audit only
    db.expire_all()
    assert db.scalar(select(NilaiMahasiswa.nilai_mentah)) == 0
    assert (
        db.scalar(select(PesertaKelasMK.kelas_mk_id).where(PesertaKelasMK.mahasiswa_id == student))
        == dataset["course_a"].id
    )
    assert (
        client.patch(base + "/kelas/" + str(b_class), json={"kode_kelas": "C"}).status_code == 409
    )


def test_closed_period_rejects_all_mutations(admin_client, dataset, db):
    client = admin_client
    period = dataset["period"]
    cohort = dataset["angkatan"].id
    db.execute(
        update(PeriodeAkademik).where(PeriodeAkademik.id == period.id).values(status="Ditutup")
    )
    db.commit()
    base = "/api/v1/periode-akademik/" + str(period.id)
    klass = str(dataset["course_a"].kelas_periode_id)
    student = str(dataset["mahasiswa"].id)
    for method, path, body in [
        ("patch", base, {"semester": "Genap"}),
        ("delete", base, None),
        (
            "post",
            base + "/kelas",
            {"angkatan_id": str(cohort), "kode_kelas": "K", "semester_studi": None},
        ),
        ("patch", base + "/kelas/" + klass, {"kode_kelas": "C"}),
        ("delete", base + "/kelas/" + klass, None),
        (
            "post",
            base + "/mahasiswa",
            {
                "mahasiswa_id": str(dataset["other_student"].id),
                "kelas_periode_id": klass,
                "status": "Aktif",
            },
        ),
        ("patch", base + "/mahasiswa/" + student, {"status": "Aktif"}),
        ("delete", base + "/mahasiswa/" + student, None),
    ]:
        assert client.request(method, path, json=body).status_code == 409
    assert client.get(base).status_code == 200
    assert client.get(base + "/kelas").status_code == 200
    assert client.get(base + "/mahasiswa").status_code == 200


def test_role_prodi_parent_and_cohort_boundaries(client, dataset, settings, db):
    for role in ["dosen", "mahasiswa"]:
        client.headers["Authorization"] = "Bearer " + create_access_token(dataset[role], settings)
        assert client.get("/api/v1/angkatan").status_code == 403
        assert (
            client.post(
                "/api/v1/periode-akademik", json={"tahun_mulai": 2030, "semester": "Ganjil"}
            ).status_code
            == 403
        )
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["admin"], settings)
    other = Prodi(kode_prodi="OTHER", nama_prodi="Other", jenjang="D4")
    db.add(other)
    db.flush()
    cur = Kurikulum(prodi_id=other.id, kode_kurikulum="OTHER", nama="Other", status="Aktif")
    foreign_period = PeriodeAkademik(prodi_id=other.id, tahun_mulai=2028, semester="Ganjil")
    db.add_all([cur, foreign_period])
    db.flush()
    foreign_cohort = Angkatan(prodi_id=other.id, tahun_masuk=2026, kurikulum_id=cur.id)
    db.add(foreign_cohort)
    db.commit()
    assert client.get("/api/v1/angkatan/" + str(foreign_cohort.id)).status_code == 404
    assert (
        client.get("/api/v1/periode-akademik/" + str(foreign_period.id) + "/kelas").status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/angkatan", json={"tahun_masuk": 2030, "kurikulum_id": str(cur.id)}
        ).status_code
        == 404
    )
    period = new_period(client)
    base = "/api/v1/periode-akademik/" + period["id"]
    assert (
        client.post(
            base + "/kelas",
            json={"angkatan_id": str(foreign_cohort.id), "kode_kelas": "A", "semester_studi": 1},
        ).status_code
        == 404
    )
    own_cur = db.get(Kurikulum, dataset["angkatan"].kurikulum_id)
    own_cur.status = "Aktif"
    db.commit()
    own_cohort = post(client, "/angkatan", {"tahun_masuk": 2024, "kurikulum_id": str(own_cur.id)})
    wrong_class = new_class(client, period["id"], own_cohort["id"])
    assert (
        client.post(
            base + "/mahasiswa",
            json={
                "mahasiswa_id": str(dataset["mahasiswa"].id),
                "kelas_periode_id": wrong_class["id"],
                "status": "Aktif",
            },
        ).status_code
        == 409
    )
    assert (
        client.get(base + "/kelas/" + str(dataset["course_a"].kelas_periode_id)).status_code == 404
    )
    assert (
        client.post(
            base + "/mahasiswa",
            json={
                "mahasiswa_id": str(dataset["dosen"].id),
                "kelas_periode_id": wrong_class["id"],
                "status": "Aktif",
            },
        ).status_code
        == 404
    )


def test_invalid_payloads_and_duplicates(admin_client, dataset):
    client = admin_client
    base = "/api/v1/periode-akademik/" + str(dataset["period"].id)
    for path, body in [
        ("/api/v1/periode-akademik", {"tahun_mulai": 2026, "semester": "Pendek"}),
        (
            "/api/v1/periode-akademik",
            {"tahun_mulai": 2028, "semester": "Ganjil", "status": "Ditutup"},
        ),
        ("/api/v1/angkatan", {"tahun_masuk": 2024.5, "kurikulum_id": str(uuid4())}),
        (
            "/api/v1/angkatan",
            {"tahun_masuk": 2024, "kurikulum_id": str(uuid4()), "prodi_id": str(uuid4())},
        ),
        (
            base + "/kelas",
            {"angkatan_id": str(dataset["angkatan"].id), "kode_kelas": "Z", "semester_studi": 1},
        ),
    ]:
        assert client.post(path, json=body).status_code == 422
    assert (
        client.post(
            base + "/kelas",
            json={
                "angkatan_id": str(dataset["angkatan"].id),
                "kode_kelas": "A",
                "semester_studi": 1,
            },
        ).status_code
        == 409
    )
    assert (
        client.patch(
            base + "/kelas/" + str(dataset["course_a"].kelas_periode_id), json={"kode_kelas": None}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/angkatan?limit=101").status_code == 422
    assert client.get(base + "/mahasiswa?offset=-1").status_code == 422


def test_atomic_roster_and_audit_failure(admin_client, dataset, db, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    before = db.scalar(select(func.count()).select_from(AuditLog))
    old_class = dataset["course_a"].kelas_periode_id

    def fail(*args, **kwargs):
        raise IntegrityError("audit failed", None, Exception())

    monkeypatch.setattr(service, "record", fail)
    path = f"/api/v1/periode-akademik/{dataset['period'].id}/mahasiswa/{dataset['mahasiswa'].id}"
    assert (
        admin_client.patch(
            path, json={"kelas_periode_id": str(dataset["course_b"].kelas_periode_id)}
        ).status_code
        == 409
    )
    db.expire_all()
    assert db.scalar(select(MahasiswaPeriode.kelas_periode_id)) == old_class
    assert db.scalar(select(PesertaKelasMK.kelas_mk_id)) == dataset["course_a"].id
    assert db.scalar(select(func.count()).select_from(AuditLog)) == before


def test_closed_period_race_blocks_roster_edit(admin_client, dataset, engine):
    user_id, period_id = dataset["admin"].id, dataset["period"].id
    started = Event()

    def worker():
        with Session(engine, expire_on_commit=False) as session:
            session.execute(text("SET lock_timeout = '5s'"))
            user = session.get(User, user_id)
            started.set()
            try:
                service.write_roster(
                    session,
                    user,
                    period_id,
                    dataset["mahasiswa"].id,
                    RosterPatch(kelas_periode_id=dataset["course_b"].kelas_periode_id),
                )
            except HTTPException as exc:
                return exc.status_code
            return 200

    with Session(engine, expire_on_commit=False) as session:
        user = session.get(User, user_id)
        locked = service.period(session, user, period_id, edit=True)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker)
            assert started.wait(5)
            import time

            deadline = time.monotonic() + 4
            blocked = False
            with engine.connect() as observer:
                while time.monotonic() < deadline:
                    observer.commit()
                    blocked = observer.scalar(
                        text(
                            "SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE wait_event_type = 'Lock' AND query LIKE '%periode_akademik%FOR UPDATE%')"
                        )
                    )
                    if blocked:
                        break
                    time.sleep(0.02)
            try:
                assert blocked
            finally:
                locked.status = "Ditutup"
                session.commit()
            assert future.result(timeout=6) == 409


def test_repeat_mk_rolls_back_new_period_roster(admin_client, dataset, db):
    client = admin_client
    period = new_period(client)
    klass = new_class(client, period["id"], dataset["angkatan"].id, "A", 1)
    k = new_class(client, period["id"], dataset["angkatan"].id, "K", None)
    design = RancanganPenilaian(
        periode_id=UUID(period["id"]),
        kurikulum_mk_id=dataset["kurikulum_mk"].id,
        dosen_id=dataset["dosen"].id,
    )
    db.add(design)
    db.flush()
    course = KelasMK(
        kelas_periode_id=UUID(klass["id"]),
        kurikulum_mk_id=dataset["kurikulum_mk"].id,
        rancangan_id=design.id,
    )
    db.add(course)
    db.commit()
    base = "/api/v1/periode-akademik/" + period["id"] + "/mahasiswa"
    student = str(dataset["mahasiswa"].id)
    assert (
        client.post(
            base, json={"mahasiswa_id": student, "kelas_periode_id": klass["id"], "status": "Aktif"}
        ).status_code
        == 409
    )
    assert client.get(base).json() == []
    assert (
        client.post(
            base, json={"mahasiswa_id": student, "kelas_periode_id": k["id"], "status": "Cuti"}
        ).status_code
        == 201
    )
    assert (
        client.patch(
            base + "/" + student, json={"kelas_periode_id": klass["id"], "status": "Aktif"}
        ).status_code
        == 409
    )
    assert client.get(base + "/" + student).json()["status"] == "Cuti"
    assert list(
        db.scalars(
            select(PesertaKelasMK.kelas_mk_id).where(PesertaKelasMK.mahasiswa_id == UUID(student))
        )
    ) == [dataset["course_a"].id]
