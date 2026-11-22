from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    CPMK,
    CPMKCPL,
    MKCPL,
    AuditLog,
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
    User,
)
from app.schemas.assessment import CopyDesign, CPMKCreate, InstrumentCreate
from app.services import assessment as service


@pytest.fixture
def dosen_client(client, dataset, settings):
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["dosen"], settings)
    return client


@pytest.fixture
def paths(dataset, db):
    base = "/api/v1/rancangan-penilaian/" + str(dataset["design"].id)
    cpmk = db.scalar(select(CPMK).where(CPMK.rancangan_id == dataset["design"].id))
    return dict(
        base=base,
        cpmk=base + "/cpmk/" + str(cpmk.id),
        sub=base + "/cpmk/" + str(cpmk.id) + "/sub-cpmk/" + str(dataset["instrument"].sub_cpmk_id),
        cpmk_id=cpmk.id,
        sub_id=dataset["instrument"].sub_cpmk_id,
        instrument_id=dataset["instrument"].id,
        instrument=base
        + "/cpmk/"
        + str(cpmk.id)
        + "/sub-cpmk/"
        + str(dataset["instrument"].sub_cpmk_id)
        + "/instrumen/"
        + str(dataset["instrument"].id),
    )


def post(client, path, body):
    response = client.post(path, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def target_design(db, dataset, year=2028, *, owner=None, mk=None):
    period = PeriodeAkademik(prodi_id=dataset["prodi"].id, tahun_mulai=year, semester="Ganjil")
    db.add(period)
    db.flush()
    klass = KelasPeriode(
        periode_id=period.id, angkatan_id=dataset["angkatan"].id, kode_kelas="A", semester_studi=1
    )
    design = RancanganPenilaian(
        periode_id=period.id,
        kurikulum_mk_id=(mk or dataset["kurikulum_mk"]).id,
        dosen_id=(owner or dataset["dosen"]).id,
    )
    db.add_all([klass, design])
    db.flush()
    course = KelasMK(
        kelas_periode_id=klass.id, kurikulum_mk_id=design.kurikulum_mk_id, rancangan_id=design.id
    )
    db.add(course)
    db.commit()
    return design, course


def mutations(paths):
    return [
        ("post", paths["base"] + "/cpmk", {"kode_cpmk": "NEW", "deskripsi": "New"}),
        ("patch", paths["cpmk"], {"deskripsi": "Changed"}),
        ("delete", paths["cpmk"], None),
        ("put", paths["cpmk"] + "/cpl", {"cpl_ids": []}),
        ("post", paths["cpmk"] + "/sub-cpmk", {"kode_sub": "NEW", "deskripsi": "New"}),
        ("patch", paths["sub"], {"deskripsi": "Changed"}),
        ("delete", paths["sub"], None),
        (
            "post",
            paths["sub"] + "/instrumen",
            {"nama_instrumen": "New", "jenis_instrumen": "Kuis", "bobot_persentase": "1.00"},
        ),
        ("patch", paths["instrument"], {"bobot_persentase": "80.00"}),
        ("delete", paths["instrument"], None),
    ]


def test_shared_detail_readiness_and_lists(dosen_client, dataset, paths):
    client = dosen_client
    result = client.get(paths["base"])
    assert result.status_code == 200, result.text
    state = result.json()
    assert state["total_bobot"] == "100.00" and state["siap_dinilai"]
    assert state["boleh_input_nilai"] and not state["struktur_terkunci"]
    assert state["tahun_akademik"] == "2026/2027" and state["semester"] == "Ganjil"
    assert client.get("/api/v1/rancangan-penilaian").json()[0]["id"] == state["id"]
    assert len(state["kelas_pengguna"]) == 2 and len(state["cpl_tersedia"]) == 1
    assert len(state["cpmk"][0]["sub_cpmk"][0]["instrumen"]) == 1
    for course in ["course_a", "course_b"]:
        assert (
            client.get(f"/api/v1/kelas-mk/{dataset[course].id}/rancangan-penilaian").json()["id"]
            == state["id"]
        )
    listed = client.get(f"/api/v1/rancangan-penilaian?periode_id={dataset['period'].id}").json()
    assert len(listed) == 1 and listed[0]["id"] == state["id"]
    assert len(client.get(paths["base"] + "/cpmk").json()) == 1
    assert len(client.get(paths["cpmk"] + "/sub-cpmk").json()) == 1
    assert len(client.get(paths["sub"] + "/instrumen").json()) == 1
    assert client.get(paths["instrument"]).status_code == 200


def test_cpmk_sub_instrument_crud_and_draft_readiness(dosen_client, dataset, paths, db):
    client = dosen_client
    cpl_id = client.get(paths["base"]).json()["cpl_tersedia"][0]["id"]
    new = post(client, paths["base"] + "/cpmk", {"kode_cpmk": "CPMK-2", "deskripsi": "Draft"})
    cp = paths["base"] + "/cpmk/" + new["id"]
    state = client.get(paths["base"]).json()
    assert state["total_bobot"] == "100.00" and not state["siap_dinilai"]
    assert any("CPMK-2" in reason for reason in state["alasan_belum_siap"])
    assert (
        client.patch(
            cp, json={"kode_cpmk": "CPMK-02", "deskripsi": "Changed", "cpl_ids": [cpl_id]}
        ).status_code
        == 200
    )
    assert client.get(paths["base"]).json()[
        "siap_dinilai"
    ]  # Required rules: mappings + total weight.
    assert (
        client.post(
            paths["base"] + "/cpmk", json={"kode_cpmk": "CPMK-1", "deskripsi": "Dup"}
        ).status_code
        == 409
    )
    sub = post(client, cp + "/sub-cpmk", {"kode_sub": "SUB-1", "deskripsi": "Draft sub"})
    sp = cp + "/sub-cpmk/" + sub["id"]
    assert (
        client.post(cp + "/sub-cpmk", json={"kode_sub": "SUB-1", "deskripsi": "Dup"}).status_code
        == 409
    )
    assert client.patch(sp, json={"kode_sub": "SUB-2", "deskripsi": "Changed"}).status_code == 200
    assert client.patch(paths["instrument"], json={"bobot_persentase": "80.00"}).status_code == 200
    instrument = post(
        client,
        sp + "/instrumen",
        {"nama_instrumen": "Kuis", "jenis_instrumen": "Kuis", "bobot_persentase": "20.00"},
    )
    ip = sp + "/instrumen/" + instrument["id"]
    assert client.get(paths["base"]).json()["siap_dinilai"]
    assert (
        client.patch(
            ip, json={"nama_instrumen": "Kuis revisi", "bobot_persentase": "10.00"}
        ).status_code
        == 200
    )
    assert client.get(paths["base"]).json()["total_bobot"] == "90.00"
    event = db.scalar(
        select(AuditLog).where(
            AuditLog.entitas_id == UUID(instrument["id"]), AuditLog.aksi == "update"
        )
    )
    assert (
        event.sebelum["bobot_persentase"] == "20.00"
        and event.sesudah["bobot_persentase"] == "10.00"
    )
    assert client.delete(ip).status_code == 204
    assert client.get(ip).status_code == 404
    assert client.delete(sp).status_code == 204
    assert client.delete(cp).status_code == 204
    assert client.get(paths["base"]).json()["total_bobot"] == "80.00"


def test_draft_cascade_deletes_no_history(dosen_client, paths, db):
    client = dosen_client
    assert client.delete(paths["instrument"]).status_code == 204
    cp = post(client, paths["base"] + "/cpmk", {"kode_cpmk": "CPMK-2", "deskripsi": "Draft"})
    cp_path = paths["base"] + "/cpmk/" + cp["id"]
    sub = post(client, cp_path + "/sub-cpmk", {"kode_sub": "S-1", "deskripsi": "Draft"})
    inst = post(
        client,
        cp_path + "/sub-cpmk/" + sub["id"] + "/instrumen",
        {"nama_instrumen": "UTS", "jenis_instrumen": "UTS", "bobot_persentase": "60.00"},
    )
    assert client.delete(cp_path).status_code == 204
    assert db.get(SubCPMK, UUID(sub["id"])) is None
    assert db.get(InstrumenPenilaian, UUID(inst["id"])) is None
    assert client.get(paths["base"]).json()["total_bobot"] == "0.00"
    assert client.delete(paths["cpmk"]).status_code == 204
    assert not client.get(paths["base"]).json()["siap_dinilai"]


def test_decimal_precision_total_limit_and_invalid_input(dosen_client, paths):
    client = dosen_client
    assert (
        client.post(
            paths["sub"] + "/instrumen",
            json={"nama_instrumen": "Over", "jenis_instrumen": "Tugas", "bobot_persentase": "0.01"},
        ).status_code
        == 409
    )
    for value in [0, -1, "100.01", "NaN", "Infinity", "10.001", True]:
        response = client.patch(paths["instrument"], json={"bobot_persentase": value})
        assert response.status_code == 422, (value, response.text)
    assert client.delete(paths["instrument"]).status_code == 204
    created = []
    for i, weight in enumerate(["33.33", 33.33, "33.34"]):
        created.append(
            post(
                client,
                paths["sub"] + "/instrumen",
                {
                    "nama_instrumen": f"Tugas {i}",
                    "jenis_instrumen": "Tugas",
                    "bobot_persentase": weight,
                },
            )
        )
    assert client.get(paths["base"]).json()["total_bobot"] == "100.00"
    ip = paths["sub"] + "/instrumen/" + created[0]["id"]
    assert client.patch(ip, json={"bobot_persentase": "33.34"}).status_code == 409
    assert client.get(ip).json()["bobot_persentase"] == "33.33"
    for method, path, body in [
        ("patch", paths["cpmk"], {}),
        ("patch", paths["cpmk"], {"deskripsi": None}),
        ("patch", paths["sub"], {"kode_sub": " "}),
        ("patch", ip, {"bobot_persentase": None}),
        (
            "post",
            paths["base"] + "/cpmk",
            {"kode_cpmk": "X", "deskripsi": "X", "rancangan_id": str(uuid4())},
        ),
    ]:
        assert client.request(method, path, json=body).status_code == 422
    assert client.get(paths["base"] + "/cpmk?limit=101").status_code == 422


def test_cpl_scoping_duplicates_and_atomic_replacement(dosen_client, dataset, paths, db):
    client = dosen_client
    source_cpl = client.get(paths["base"]).json()["cpl_tersedia"][0]["id"]
    other = MasterCPL(
        kurikulum_id=dataset["angkatan"].kurikulum_id,
        prodi_id=dataset["prodi"].id,
        kode_cpl="OTHER",
        kategori="P",
        deskripsi="Not mapped",
    )
    national = MasterCPL(
        kurikulum_id=dataset["angkatan"].kurikulum_id,
        prodi_id=None,
        kode_cpl="S-01",
        kategori="S",
        deskripsi="National",
    )
    db.add_all([other, national])
    db.flush()
    db.add(MKCPL(kurikulum_mk_id=dataset["kurikulum_mk"].id, cpl_id=national.id))
    db.commit()
    assert (
        client.put(
            paths["cpmk"] + "/cpl", json={"cpl_ids": [source_cpl, str(national.id)]}
        ).status_code
        == 200
    )
    before = client.get(paths["cpmk"]).json()
    assert (
        client.put(
            paths["cpmk"] + "/cpl", json={"cpl_ids": [source_cpl, str(other.id)]}
        ).status_code
        == 404
    )
    assert client.get(paths["cpmk"]).json() == before
    assert client.put(paths["cpmk"] + "/cpl", json={"cpl_ids": [source_cpl] * 2}).status_code == 422
    assert (
        client.post(
            paths["base"] + "/cpmk",
            json={"kode_cpmk": "FAIL", "deskripsi": "Invalid mapping", "cpl_ids": [str(other.id)]},
        ).status_code
        == 404
    )
    assert len(client.get(paths["base"] + "/cpmk").json()) == 1
    assert client.put(paths["cpmk"] + "/cpl", json={"cpl_ids": []}).status_code == 200
    assert not client.get(paths["base"]).json()["siap_dinilai"]
    assert db.get(MasterCPL, national.id).deskripsi == "National"
    assert (
        client.patch(
            f"/api/v1/kurikulum/{dataset['angkatan'].kurikulum_id}/cpl/{national.id}",
            json={"deskripsi": "Forbidden"},
        ).status_code
        == 403
    )


@pytest.mark.parametrize("closed", [False, True])
def test_every_structural_mutation_frozen_with_grade_or_closed(
    dosen_client, dataset, paths, db, closed
):
    if closed:
        db.execute(
            update(PeriodeAkademik)
            .where(PeriodeAkademik.id == dataset["period"].id)
            .values(status="Ditutup")
        )
    else:
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
    before = db.scalar(select(func.count()).select_from(AuditLog))
    for method, path, body in mutations(paths):
        response = dosen_client.request(method, path, json=body)
        assert response.status_code == 409, (path, response.text)
    state = dosen_client.get(
        f"/api/v1/kelas-mk/{dataset['course_b'].id}/rancangan-penilaian"
    ).json()
    assert state["struktur_terkunci"] and state["siap_dinilai"]
    assert state["boleh_input_nilai"] == (not closed)
    assert state["total_bobot"] == "100.00"
    assert dosen_client.get(paths["instrument"]).status_code == 200
    assert db.scalar(select(func.count()).select_from(AuditLog)) == before
    if not closed:
        db.execute(
            update(PeriodeAkademik)
            .where(PeriodeAkademik.id == dataset["period"].id)
            .values(status="Ditutup")
        )
        db.commit()
        db.execute(
            update(PeriodeAkademik)
            .where(PeriodeAkademik.id == dataset["period"].id)
            .values(status="Dibuka")
        )
        db.commit()
        assert (
            dosen_client.patch(paths["instrument"], json={"bobot_persentase": "80.00"}).status_code
            == 409
        )
        assert db.scalar(select(NilaiMahasiswa.nilai_mentah)) == 0


def test_copy_closed_graded_source_to_empty_target_with_new_ids(dosen_client, dataset, paths, db):
    client = dosen_client
    target, _ = target_design(db, dataset)
    db.add(
        NilaiMahasiswa(
            instrumen_id=dataset["instrument"].id,
            kelas_mk_id=dataset["course_a"].id,
            mahasiswa_id=dataset["mahasiswa"].id,
            nilai_mentah=0,
            diubah_oleh=dataset["dosen"].id,
        )
    )
    db.execute(
        update(PeriodeAkademik)
        .where(PeriodeAkademik.id == dataset["period"].id)
        .values(status="Ditutup")
    )
    db.commit()
    tp = "/api/v1/rancangan-penilaian/" + str(target.id)
    result = client.post(tp + "/salin", json={"sumber_rancangan_id": str(dataset["design"].id)})
    assert result.status_code == 200, result.text
    state = result.json()
    assert state["sumber_rancangan_id"] == str(dataset["design"].id)
    assert state["siap_dinilai"] and state["boleh_input_nilai"] and not state["struktur_terkunci"]
    cpmk = state["cpmk"][0]
    sub = cpmk["sub_cpmk"][0]
    inst = sub["instrumen"][0]
    assert (
        cpmk["id"] != str(paths["cpmk_id"])
        and sub["id"] != str(paths["sub_id"])
        and inst["id"] != str(paths["instrument_id"])
    )
    assert cpmk["cpl_ids"] == client.get(paths["cpmk"]).json()["cpl_ids"]
    ip = tp + "/cpmk/" + cpmk["id"] + "/sub-cpmk/" + sub["id"] + "/instrumen/" + inst["id"]
    assert client.patch(ip, json={"bobot_persentase": "80.00"}).status_code == 200
    assert client.get(paths["instrument"]).json()["bobot_persentase"] == "100.00"
    assert (
        client.post(
            tp + "/salin", json={"sumber_rancangan_id": str(dataset["design"].id)}
        ).status_code
        == 409
    )
    assert db.scalar(select(func.count()).select_from(NilaiMahasiswa)) == 1
    assert db.scalar(select(NilaiMahasiswa.nilai_mentah)) == 0
    assert len(state["kelas_pengguna"]) == 1


def test_copy_rejects_same_period_other_mk_filled_target_and_foreign_owner(
    dosen_client, dataset, paths, db
):
    client = dosen_client
    assert (
        client.post(
            paths["base"] + "/salin", json={"sumber_rancangan_id": str(dataset["design"].id)}
        ).status_code
        == 409
    )
    target, _ = target_design(db, dataset)
    tp = "/api/v1/rancangan-penilaian/" + str(target.id)
    post(client, tp + "/cpmk", {"kode_cpmk": "EMPTY-CPMK", "deskripsi": "No instruments"})
    assert (
        client.post(
            tp + "/salin", json={"sumber_rancangan_id": str(dataset["design"].id)}
        ).status_code
        == 409
    )
    wrong_mk = KurikulumMK(
        kurikulum_id=dataset["angkatan"].kurikulum_id,
        mk_id=dataset["mk"].id,
        nama_mk="Other",
        sks=3,
        semester=1,
    )
    # A new curriculum version gives the same master MK a different kurikulum_mk identity.
    kur = Kurikulum(prodi_id=dataset["prodi"].id, kode_kurikulum="COPY-OTHER", nama="Other")
    db.add(kur)
    db.flush()
    wrong_mk.kurikulum_id = kur.id
    db.add(wrong_mk)
    db.commit()
    foreign_target, _ = target_design(db, dataset, year=2029, mk=wrong_mk)
    assert (
        client.post(
            f"/api/v1/rancangan-penilaian/{foreign_target.id}/salin",
            json={"sumber_rancangan_id": str(dataset["design"].id)},
        ).status_code
        == 409
    )
    other_owner, _ = target_design(db, dataset, year=2030, owner=dataset["outsider"])
    assert (
        client.post(tp + "/salin", json={"sumber_rancangan_id": str(other_owner.id)}).status_code
        == 404
    )


def test_role_assignment_parent_and_prodi_boundaries(client, dataset, paths, db, settings):
    for role in ["admin", "mahasiswa"]:
        headers = {"Authorization": "Bearer " + create_access_token(dataset[role], settings)}
        assert client.get(paths["base"], headers=headers).status_code == 403
        assert (
            client.post(
                paths["base"] + "/cpmk",
                json={"kode_cpmk": "NO", "deskripsi": "No"},
                headers=headers,
            ).status_code
            == 403
        )
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["outsider"], settings)
    assert client.get(paths["base"]).status_code == 404
    assert (
        client.get(f"/api/v1/kelas-mk/{dataset['course_a'].id}/rancangan-penilaian").status_code
        == 404
    )
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["dosen"], settings)
    cp = post(client, paths["base"] + "/cpmk", {"kode_cpmk": "CPMK-2", "deskripsi": "Other parent"})
    other_sub = post(
        client,
        paths["base"] + "/cpmk/" + cp["id"] + "/sub-cpmk",
        {"kode_sub": "SUB-1", "deskripsi": "Other"},
    )
    assert client.get(paths["cpmk"] + "/sub-cpmk/" + other_sub["id"]).status_code == 404
    assert (
        client.patch(
            paths["cpmk"] + "/sub-cpmk/" + other_sub["id"], json={"deskripsi": "No"}
        ).status_code
        == 404
    )
    orphan, course = target_design(db, dataset)
    db.delete(course)
    db.commit()
    assert client.get(f"/api/v1/rancangan-penilaian/{orphan.id}").status_code == 404
    other_prodi = Prodi(kode_prodi="OTHER", nama_prodi="Other", jenjang="D4")
    db.add(other_prodi)
    db.flush()
    db.execute(update(User).where(User.id == dataset["dosen"].id).values(prodi_id=other_prodi.id))
    db.commit()
    assert client.get(paths["base"]).status_code == 404


def test_audit_failure_rolls_back_cpmk_mapping_and_copy(
    dosen_client, dataset, paths, db, monkeypatch
):
    from sqlalchemy.exc import IntegrityError

    target, _ = target_design(db, dataset)
    before = {
        model: db.scalar(select(func.count()).select_from(model))
        for model in [CPMK, SubCPMK, InstrumenPenilaian, CPMKCPL, AuditLog]
    }

    def fail(*args, **kwargs):
        raise IntegrityError("Audit failure", None, Exception())

    monkeypatch.setattr(service.academic, "record", fail)
    cpl_id = dosen_client.get(paths["base"]).json()["cpl_tersedia"][0]["id"]
    assert (
        dosen_client.post(
            paths["base"] + "/cpmk",
            json={"kode_cpmk": "ROLLBACK", "deskripsi": "Rollback", "cpl_ids": [cpl_id]},
        ).status_code
        == 409
    )
    assert (
        dosen_client.post(
            f"/api/v1/rancangan-penilaian/{target.id}/salin",
            json={"sumber_rancangan_id": str(dataset["design"].id)},
        ).status_code
        == 409
    )
    for model, count in before.items():
        assert db.scalar(select(func.count()).select_from(model)) == count
    db.expire_all()
    assert db.get(RancanganPenilaian, target.id).sumber_rancangan_id is None


def test_two_concurrent_instruments_cannot_exceed_total(dosen_client, dataset, paths, db, engine):
    assert dosen_client.delete(paths["instrument"]).status_code == 204

    def worker(index):
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, dataset["dosen"].id)
            try:
                service.create_instrument(
                    session,
                    user,
                    dataset["design"].id,
                    paths["cpmk_id"],
                    paths["sub_id"],
                    InstrumentCreate(
                        nama_instrumen=f"Concurrent {index}",
                        jenis_instrumen="Tugas",
                        bobot_persentase="60.00",
                    ),
                )
            except HTTPException as exc:
                return exc.status_code
            return 201

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, [1, 2]))
    assert sorted(results) == [201, 409]
    assert dosen_client.get(paths["base"]).json()["total_bobot"] == "60.00"


def test_concurrent_grade_entry_freezes_waiting_structure_edit(
    dosen_client, dataset, paths, engine
):
    started = Event()

    def worker():
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, dataset["dosen"].id)
            started.set()
            try:
                service.create_cpmk(
                    session,
                    user,
                    dataset["design"].id,
                    CPMKCreate(kode_cpmk="RACE", deskripsi="Race"),
                )
            except HTTPException as exc:
                return exc.status_code
            return 201

    with Session(engine, expire_on_commit=False) as session:
        user = session.get(User, dataset["dosen"].id)
        service.editable(session, user, dataset["design"].id)
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
                session.add(
                    NilaiMahasiswa(
                        instrumen_id=dataset["instrument"].id,
                        kelas_mk_id=dataset["course_a"].id,
                        mahasiswa_id=dataset["mahasiswa"].id,
                        nilai_mentah=0,
                        diubah_oleh=dataset["dosen"].id,
                    )
                )
                session.commit()
            assert future.result(timeout=6) == 409
    assert dosen_client.get(paths["base"]).json()["struktur_terkunci"]


def test_two_copies_into_same_empty_target_are_serialized(dosen_client, dataset, db, engine):
    target, _ = target_design(db, dataset)

    def worker():
        with Session(engine, expire_on_commit=False) as session:
            try:
                service.copy_design(
                    session,
                    session.get(User, dataset["dosen"].id),
                    target.id,
                    CopyDesign(sumber_rancangan_id=dataset["design"].id),
                )
            except HTTPException as exc:
                return exc.status_code
            return 200

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(results) == [200, 409]
    assert (
        db.scalar(select(func.count()).select_from(CPMK).where(CPMK.rancangan_id == target.id)) == 1
    )


def test_copy_incomplete_draft_keeps_missing_mapping_and_weight(dosen_client, dataset, paths, db):
    client = dosen_client
    assert client.patch(paths["instrument"], json={"bobot_persentase": "80.00"}).status_code == 200
    post(
        client, paths["base"] + "/cpmk", {"kode_cpmk": "UNMAPPED", "deskripsi": "Draft without CPL"}
    )
    target, _ = target_design(db, dataset)
    result = client.post(
        f"/api/v1/rancangan-penilaian/{target.id}/salin",
        json={"sumber_rancangan_id": str(dataset["design"].id)},
    )
    assert result.status_code == 200, result.text
    copied = result.json()
    assert copied["total_bobot"] == "80.00" and not copied["siap_dinilai"]
    assert not copied["struktur_terkunci"]
    assert next(row for row in copied["cpmk"] if row["kode_cpmk"] == "UNMAPPED")["cpl_ids"] == []
