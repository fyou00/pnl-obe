from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    AuditLog,
    KelasMK,
    Kurikulum,
    Mahasiswa,
    MataKuliah,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    Prodi,
    RancanganPenilaian,
    User,
)
from app.schemas.teaching import ApplyPackage
from app.services import teaching as service


@pytest.fixture
def admin_client(client, dataset, settings):
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["admin"], settings)
    return client


def post(client, path, payload):
    response = client.post("/api/v1" + path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def package(admin_client, dataset, db):
    client = admin_client
    source = str(dataset["angkatan"].kurikulum_id)
    cloned = post(
        client, f"/kurikulum/{source}/salin", {"kode_kurikulum": "PAKET", "nama": "Paket test"}
    )
    mk = post(client, "/mata-kuliah", {"kode_mk": "SECOND", "nama_mk": "Algoritma"})
    second = post(
        client,
        f"/kurikulum/{cloned['id']}/mata-kuliah",
        {"mk_id": mk["id"], "nama_mk": "Algoritma", "sks": 3, "semester": 1},
    )
    cpl = client.get(f"/api/v1/kurikulum/{cloned['id']}/cpl").json()[0]
    assert (
        client.put(
            f"/api/v1/kurikulum/{cloned['id']}/mata-kuliah/{second['id']}/cpl",
            json={"items": [{"cpl_id": cpl["id"]}]},
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/kurikulum/{cloned['id']}/aktifkan").status_code == 200
    cohort = post(client, "/angkatan", {"tahun_masuk": 2024, "kurikulum_id": cloned["id"]})
    period = post(client, "/periode-akademik", {"tahun_mulai": 2027, "semester": "Ganjil"})
    classes = {}
    for code in ["A", "B", "C", "K"]:
        classes[code] = post(
            client,
            f"/periode-akademik/{period['id']}/kelas",
            {
                "angkatan_id": cohort["id"],
                "kode_kelas": code,
                "semester_studi": None if code == "K" else 1,
            },
        )
    students = {}
    for code in ["A", "B", "K"]:
        account = User(
            prodi_id=dataset["prodi"].id,
            nama=f"Student {code}",
            nim_nidn=f"PKT-{code}",
            email=f"pkt-{code.lower()}@example.com",
            password_hash=dataset["mahasiswa"].password_hash,
            role="Mahasiswa",
        )
        db.add(account)
        db.flush()
        db.add(Mahasiswa(id=account.id, angkatan_id=UUID(cohort["id"])))
        db.commit()
        students[code] = account.id
        post(
            client,
            f"/periode-akademik/{period['id']}/mahasiswa",
            {
                "mahasiswa_id": str(account.id),
                "kelas_periode_id": classes[code]["id"],
                "status": "Cuti" if code == "K" else "Aktif",
            },
        )
    base = f"/api/v1/periode-akademik/{period['id']}/angkatan/{cohort['id']}/paket"
    preview = client.get(base)
    assert preview.status_code == 200, preview.text
    preview = preview.json()
    assignments = []
    for pair in preview["penugasan"]:
        # A/B share one lecturer; C uses another lecturer, for both MKs.
        dosen = (
            dataset["outsider"]
            if pair["kelas_periode_id"] == classes["C"]["id"]
            else dataset["dosen"]
        )
        assignments.append(
            {
                **{k: pair[k] for k in ["kelas_periode_id", "kurikulum_mk_id"]},
                "dosen_id": str(dosen.id),
            }
        )
    return dict(
        base=base,
        payload={"penugasan": assignments},
        preview=preview,
        classes=classes,
        students=students,
        period=period,
        cohort=cohort,
        curriculum=cloned,
    )


def row_counts(db):
    return {
        model: db.scalar(select(func.count()).select_from(model))
        for model in [KelasMK, RancanganPenilaian, PesertaKelasMK, AuditLog]
    }


def apply(client, package, body=None):
    return client.post(
        package["base"] + "/terapkan", json=package["payload"] if body is None else body
    )


def test_preview_apply_shared_design_k_exclusion_and_repeat(admin_client, dataset, package, db):
    client = admin_client
    assert len(package["preview"]["kelas"]) == 3 and len(package["preview"]["penugasan"]) == 6
    assert all(row["dosen_id"] is None for row in package["preview"]["penugasan"])
    response = apply(client, package)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["total_kelas_mk"] == result["kelas_mk_dibuat"] == 6
    assert result["rancangan_dibuat"] == 4
    assert result["total_peserta"] == result["peserta_ditambahkan"] == 4
    preview = client.get(package["base"]).json()
    for course in preview["mata_kuliah"]:
        rows = {
            row["kelas_periode_id"]: row
            for row in preview["penugasan"]
            if row["kurikulum_mk_id"] == course["kurikulum_mk_id"]
        }
        assert (
            rows[package["classes"]["A"]["id"]]["rancangan_id"]
            == rows[package["classes"]["B"]["id"]]["rancangan_id"]
        )
        assert (
            rows[package["classes"]["C"]["id"]]["rancangan_id"]
            != rows[package["classes"]["A"]["id"]]["rancangan_id"]
        )
    assert not db.scalar(
        select(KelasMK.id).where(KelasMK.kelas_periode_id == UUID(package["classes"]["K"]["id"]))
    )
    assert not db.scalar(
        select(PesertaKelasMK.kelas_mk_id).where(
            PesertaKelasMK.mahasiswa_id == package["students"]["K"]
        )
    )
    before = row_counts(db)
    repeat = apply(client, package)
    assert repeat.status_code == 200
    assert all(
        repeat.json()[key] == 0
        for key in [
            "kelas_mk_dibuat",
            "rancangan_dibuat",
            "kelas_mk_diperbarui",
            "peserta_ditambahkan",
        ]
    )
    assert row_counts(db) == before
    cohort_url = "/api/v1/angkatan/" + package["cohort"]["id"]
    assert (
        client.patch(
            cohort_url, json={"kurikulum_id": str(dataset["angkatan"].kurikulum_id)}
        ).status_code
        == 409
    )
    # Existing access APIs immediately show the assigned classes and enrollments.
    token = create_access_token(dataset["dosen"], client.app.state.settings)
    assigned = client.get(
        "/api/v1/kelas-mk?periode_id=" + package["period"]["id"],
        headers={"Authorization": "Bearer " + token},
    )
    assert len(assigned.json()) == 4
    student = db.get(User, package["students"]["A"])
    token = create_access_token(student, client.app.state.settings)
    enrolled = client.get(
        "/api/v1/kelas-mk?periode_id=" + package["period"]["id"],
        headers={"Authorization": "Bearer " + token},
    )
    assert len(enrolled.json()) == 2


def test_complete_assignments_duplicates_and_invalid_teacher(admin_client, dataset, package, db):
    before = row_counts(db)
    body = deepcopy(package["payload"])
    body["penugasan"].pop()
    assert apply(admin_client, package, body).status_code == 409
    body = deepcopy(package["payload"])
    body["penugasan"].append(body["penugasan"][0])
    assert apply(admin_client, package, body).status_code == 422
    body = deepcopy(package["payload"])
    body["penugasan"][0]["kelas_periode_id"] = package["classes"]["K"]["id"]
    assert apply(admin_client, package, body).status_code == 404
    body = deepcopy(package["payload"])
    body["penugasan"][0]["kurikulum_mk_id"] = str(dataset["kurikulum_mk"].id)
    assert apply(admin_client, package, body).status_code == 404
    for lecturer in [dataset["mahasiswa"], dataset["admin"]]:
        body = deepcopy(package["payload"])
        body["penugasan"][0]["dosen_id"] = str(lecturer.id)
        assert apply(admin_client, package, body).status_code == 409
    db.execute(update(User).where(User.id == dataset["outsider"].id).values(aktif=False))
    db.commit()
    assert apply(admin_client, package).status_code == 409
    assert row_counts(db) == before


def test_atomic_mid_batch_failure_and_no_repeat_mk(admin_client, dataset, package, db):
    # The same student already took one package master MK in another period.
    master_mk = dataset["mk"].id
    student = package["students"]["B"]
    db.add(
        PesertaKelasMK(kelas_mk_id=dataset["course_a"].id, mahasiswa_id=student, mk_id=master_mk)
    )
    db.commit()
    before = row_counts(db)
    result = apply(admin_client, package)
    assert result.status_code == 409, result.text
    assert row_counts(db) == before
    assert all(
        row["kelas_mk_id"] is None for row in admin_client.get(package["base"]).json()["penugasan"]
    )


def test_reassign_shared_target_preserve_old_design_and_noop(admin_client, dataset, package, db):
    assert apply(admin_client, package).status_code == 200
    pairs = admin_client.get(package["base"]).json()["penugasan"]
    a = next(row for row in pairs if row["kelas_periode_id"] == package["classes"]["A"]["id"])
    c = next(
        row
        for row in pairs
        if row["kelas_periode_id"] == package["classes"]["C"]["id"]
        and row["kurikulum_mk_id"] == a["kurikulum_mk_id"]
    )
    path = "/api/v1/kelas-mk/" + c["kelas_mk_id"] + "/pengampu"
    old_design = UUID(c["rancangan_id"])
    old_counts = row_counts(db)
    response = admin_client.patch(path, json={"dosen_id": str(dataset["dosen"].id)})
    assert response.status_code == 200
    assert response.json()["rancangan_id"] == a["rancangan_id"]
    assert db.get(RancanganPenilaian, old_design) is not None
    assert row_counts(db)[RancanganPenilaian] == old_counts[RancanganPenilaian]
    before = row_counts(db)
    assert admin_client.patch(path, json={"dosen_id": str(dataset["dosen"].id)}).status_code == 200
    assert row_counts(db) == before
    # Bulk desired assignments can also correct a pre-grade assignment atomically.
    response = apply(admin_client, package)
    assert response.status_code == 200 and response.json()["kelas_mk_diperbarui"] == 1
    db.expire_all()
    assert db.get(KelasMK, UUID(c["kelas_mk_id"])).rancangan_id == old_design


def test_reapply_with_grades_preserves_scores_and_blocks_reassignment(admin_client, dataset, db):
    source = str(dataset["angkatan"].kurikulum_id)
    assert admin_client.post("/api/v1/kurikulum/" + source + "/aktifkan").status_code == 200
    db.add(
        NilaiMahasiswa(
            instrumen_id=dataset["instrument"].id,
            kelas_mk_id=dataset["course_a"].id,
            mahasiswa_id=dataset["mahasiswa"].id,
            nilai_mentah=0,
            diubah_oleh=dataset["dosen"].id,
        )
    )
    db.commit()
    base = (
        f"/api/v1/periode-akademik/{dataset['period'].id}/angkatan/{dataset['angkatan'].id}/paket"
    )
    pairs = admin_client.get(base).json()["penugasan"]
    payload = {
        "penugasan": [
            {
                **{k: row[k] for k in ["kelas_periode_id", "kurikulum_mk_id"]},
                "dosen_id": str(dataset["dosen"].id),
            }
            for row in pairs
        ]
    }
    before = row_counts(db)
    assert admin_client.post(base + "/terapkan", json=payload).status_code == 200
    assert row_counts(db) == before
    path = f"/api/v1/kelas-mk/{dataset['course_a'].id}/pengampu"
    assert (
        admin_client.patch(path, json={"dosen_id": str(dataset["outsider"].id)}).status_code == 409
    )
    body = deepcopy(payload)
    body["penugasan"][0]["dosen_id"] = str(dataset["outsider"].id)
    # Explicitly select the graded class even if preview sort changes.
    next(
        item
        for item in body["penugasan"]
        if item["kelas_periode_id"] == str(dataset["course_a"].kelas_periode_id)
    )["dosen_id"] = str(dataset["outsider"].id)
    assert admin_client.post(base + "/terapkan", json=body).status_code == 409
    assert row_counts(db) == before
    assert db.scalar(select(NilaiMahasiswa.nilai_mentah)) == 0


def test_closed_period_is_readonly_and_draft_not_applicable(admin_client, dataset, package, db):
    # Legacy fixture is Draft; neither preview nor apply should make it a valid package.
    base = (
        f"/api/v1/periode-akademik/{dataset['period'].id}/angkatan/{dataset['angkatan'].id}/paket"
    )
    assert admin_client.get(base).status_code == 409
    db.execute(
        update(PeriodeAkademik)
        .where(PeriodeAkademik.id == UUID(package["period"]["id"]))
        .values(status="Ditutup")
    )
    db.commit()
    assert admin_client.get(package["base"]).status_code == 200
    assert apply(admin_client, package).status_code == 409


def test_archived_cohort_and_inactive_master_still_uses_snapshot(admin_client, package, db):
    db.execute(
        update(Kurikulum)
        .where(Kurikulum.id == UUID(package["curriculum"]["id"]))
        .values(status="Arsip")
    )
    first_master = UUID(package["preview"]["mata_kuliah"][0]["mk_id"])
    db.execute(update(MataKuliah).where(MataKuliah.id == first_master).values(aktif=False))
    db.commit()
    assert apply(admin_client, package).status_code == 200


def test_roster_invalidity_and_participant_mismatch_are_not_silently_deleted(
    admin_client, dataset, package, db
):
    db.execute(update(User).where(User.id == package["students"]["A"]).values(aktif=False))
    db.commit()
    assert apply(admin_client, package).status_code == 409
    db.execute(update(User).where(User.id == package["students"]["A"]).values(aktif=True))
    db.commit()
    assert apply(admin_client, package).status_code == 200
    pair = admin_client.get(package["base"]).json()["penugasan"][0]
    db.add(
        PesertaKelasMK(
            kelas_mk_id=UUID(pair["kelas_mk_id"]),
            mahasiswa_id=dataset["other_student"].id,
            mk_id=UUID(
                next(
                    row["mk_id"]
                    for row in package["preview"]["mata_kuliah"]
                    if row["kurikulum_mk_id"] == pair["kurikulum_mk_id"]
                )
            ),
        )
    )
    db.commit()
    before = row_counts(db)
    assert apply(admin_client, package).status_code == 409
    assert row_counts(db) == before


def test_lecturer_listing_roles_scope_and_foreign_ids(admin_client, dataset, package, db, settings):
    client = admin_client
    response = client.get("/api/v1/dosen?q=Test")
    assert response.status_code == 200 and len(response.json()) == 1
    assert "password" not in response.text and "token_version" not in response.text
    for role in ["dosen", "mahasiswa"]:
        token = create_access_token(dataset[role], settings)
        headers = {"Authorization": "Bearer " + token}
        assert client.get(package["base"], headers=headers).status_code == 403
        assert (
            client.post(
                package["base"] + "/terapkan", json=package["payload"], headers=headers
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f"/api/v1/kelas-mk/{dataset['course_a'].id}/pengampu",
                json={"dosen_id": str(dataset["dosen"].id)},
                headers=headers,
            ).status_code
            == 403
        )
        assert client.get("/api/v1/dosen", headers=headers).status_code == 403
    foreign = Prodi(kode_prodi="OTHER", nama_prodi="Other", jenjang="D4")
    db.add(foreign)
    db.flush()
    account = User(
        prodi_id=foreign.id,
        nim_nidn="FOREIGN",
        nama="Foreign",
        email="foreign@example.com",
        password_hash=dataset["dosen"].password_hash,
        role="Dosen",
    )
    period = PeriodeAkademik(prodi_id=foreign.id, tahun_mulai=2027, semester="Ganjil")
    db.add_all([account, period])
    db.commit()
    body = deepcopy(package["payload"])
    body["penugasan"][0]["dosen_id"] = str(account.id)
    assert apply(client, package, body).status_code == 404
    assert str(account.id) not in client.get("/api/v1/dosen").text
    assert (
        client.get(
            f"/api/v1/periode-akademik/{period.id}/angkatan/{package['cohort']['id']}/paket"
        ).status_code
        == 404
    )
    assert (
        client.patch(
            "/api/v1/kelas-mk/" + str(uuid4()) + "/pengampu",
            json={"dosen_id": str(dataset["dosen"].id)},
        ).status_code
        == 404
    )


def test_audit_failure_rolls_back_entire_package(admin_client, package, db, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    original = service.academic.record

    def fail_final(db, user, action, row, *args, **kwargs):
        if action == "apply_package":
            raise IntegrityError("audit failure", None, Exception())
        return original(db, user, action, row, *args, **kwargs)

    monkeypatch.setattr(service.academic, "record", fail_final)
    before = row_counts(db)
    assert apply(admin_client, package).status_code == 409
    assert row_counts(db) == before


def test_two_concurrent_applications_are_idempotent(admin_client, dataset, package, engine, db):
    payload = ApplyPackage.model_validate(package["payload"])
    user_id = dataset["admin"].id
    period_id, cohort_id = UUID(package["period"]["id"]), UUID(package["cohort"]["id"])

    def worker():
        with Session(engine, expire_on_commit=False) as session:
            return service.apply(session, session.get(User, user_id), period_id, cohort_id, payload)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(result.kelas_mk_dibuat for result in results) == [0, 6]
    assert sorted(result.peserta_ditambahkan for result in results) == [0, 4]
    assert (
        db.scalar(
            select(func.count())
            .select_from(KelasMK)
            .where(
                KelasMK.kelas_periode_id.in_(
                    [UUID(package["classes"][code]["id"]) for code in ["A", "B", "C"]]
                )
            )
        )
        == 6
    )
