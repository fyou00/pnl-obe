from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import AuditLog, Kurikulum, KurikulumMK, MasterCPL, MataKuliah, Prodi, User
from app.schemas.curriculum import KurikulumPatch, MatriksReplace
from app.services import curriculum as service


@pytest.fixture
def admin_client(client, dataset, settings):
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["admin"], settings)
    return client


def post(client, path, payload):
    response = client.post("/api/v1" + path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def build(client, suffix="1", mapped=True):
    master = post(client, "/mata-kuliah", {"kode_mk": "NEW-" + suffix, "nama_mk": "MK Baru"})
    kur = post(client, "/kurikulum", {"kode_kurikulum": "K-" + suffix, "nama": "Kurikulum Baru"})
    base = "/api/v1/kurikulum/" + kur["id"]
    paket = post(
        client,
        f"/kurikulum/{kur['id']}/mata-kuliah",
        {"mk_id": master["id"], "nama_mk": "Nama snapshot", "sks": 3, "semester": 1},
    )
    cpl = post(
        client,
        f"/kurikulum/{kur['id']}/cpl",
        {"kode_cpl": "P-01", "kategori": "P", "deskripsi": "Pengetahuan"},
    )
    matrix = base + "/mata-kuliah/" + paket["id"] + "/cpl"
    if mapped:
        assert (
            client.put(matrix, json={"items": [{"cpl_id": cpl["id"], "urutan_rps": 1}]}).status_code
            == 200
        )
    return dict(master=master, kur=kur, paket=paket, cpl=cpl, base=base, matrix=matrix)


def test_master_crud_snapshot_and_disable(admin_client, db):
    client = admin_client
    item = post(client, "/mata-kuliah", {"kode_mk": "UNUSED", "nama_mk": "Unused"})
    url = "/api/v1/mata-kuliah/" + item["id"]
    assert client.get(url).json()["nama_mk"] == "Unused"
    assert client.patch(url, json={"kode_mk": "RENAMED", "deskripsi": None}).status_code == 200
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    data = build(client)
    url = "/api/v1/mata-kuliah/" + data["master"]["id"]
    assert client.patch(url, json={"kode_mk": "CHANGED"}).status_code == 409
    assert client.delete(url).status_code == 409
    assert client.patch(url, json={"nama_mk": "Nama baru", "aktif": False}).status_code == 200
    assert (
        client.get(data["base"] + "/mata-kuliah/" + data["paket"]["id"]).json()["nama_mk"]
        == "Nama snapshot"
    )
    assert len(client.get("/api/v1/mata-kuliah?q=nama%20baru&limit=1").json()) == 1
    assert client.get("/api/v1/mata-kuliah?q=%25").json() == []  # literal, not wildcard
    other = post(client, "/kurikulum", {"kode_kurikulum": "OTHER", "nama": "Other"})
    response = client.post(
        "/api/v1/kurikulum/" + other["id"] + "/mata-kuliah",
        json={"mk_id": data["master"]["id"], "nama_mk": "Not active", "sks": 1, "semester": 1},
    )
    assert response.status_code == 409
    records = list(db.scalars(select(AuditLog).where(AuditLog.entitas_id == UUID(item["id"]))))
    assert [r.aksi for r in records] == ["create", "update", "delete"]
    assert records[1].sebelum["kode_mk"] == "UNUSED"
    assert records[1].sesudah["kode_mk"] == "RENAMED"


def test_draft_crud_and_atomic_deletion(admin_client, db):
    client = admin_client
    data = build(client)
    base, paket, cpl = data["base"], data["paket"], data["cpl"]
    assert client.patch(base, json={"nama": "Changed"}).json()["nama"] == "Changed"
    assert (
        client.patch(
            base + "/mata-kuliah/" + paket["id"], json={"semester": 3, "sks": 4}
        ).status_code
        == 200
    )
    assert client.get(base + "/mata-kuliah?semester=1").json() == []
    assert len(client.get(base + "/mata-kuliah?semester=3&q=Snapshot").json()) == 1
    assert (
        client.patch(base + "/cpl/" + cpl["id"], json={"deskripsi": "Changed CPL"}).status_code
        == 200
    )
    assert client.get(base + "/cpl?q=Changed").json()[0]["id"] == cpl["id"]
    assert client.delete(base + "/cpl/" + cpl["id"]).status_code == 409
    assert client.put(data["matrix"], json={"items": []}).status_code == 200
    assert client.delete(base + "/cpl/" + cpl["id"]).status_code == 204
    assert client.delete(base + "/mata-kuliah/" + paket["id"]).status_code == 204
    assert client.delete(base).status_code == 204
    data = build(client, "2")
    assert client.delete(data["base"]).status_code == 204  # also deletes unused children/matrix
    assert db.get(MasterCPL, UUID(data["cpl"]["id"])) is None
    assert db.get(KurikulumMK, UUID(data["paket"]["id"])) is None
    assert db.get(MataKuliah, UUID(data["master"]["id"])) is not None


def test_activation_archive_and_frozen_contents(admin_client):
    client = admin_client
    data = build(client, mapped=False)
    base = data["base"]
    assert client.post(base + "/aktifkan").status_code == 409
    assert client.post(base + "/arsipkan").status_code == 409
    assert (
        client.put(data["matrix"], json={"items": [{"cpl_id": data["cpl"]["id"]}]}).status_code
        == 200
    )
    assert client.post(base + "/aktifkan").json()["status"] == "Aktif"
    for status in ["Aktif", "Arsip"]:
        assert (
            client.get("/api/v1/kurikulum?status=" + status + "&q=K-1").json()[0]["id"]
            == data["kur"]["id"]
        )
        assert client.patch(base, json={"nama": "Forbidden"}).status_code == 409
        assert client.delete(base).status_code == 409
        assert (
            client.post(
                base + "/cpl", json={"kode_cpl": "X", "kategori": "S", "deskripsi": "Test"}
            ).status_code
            == 409
        )
        assert (
            client.patch(
                base + "/cpl/" + data["cpl"]["id"], json={"deskripsi": "Forbidden"}
            ).status_code
            == 409
        )
        assert client.delete(base + "/cpl/" + data["cpl"]["id"]).status_code == 409
        assert (
            client.post(
                base + "/mata-kuliah",
                json={"mk_id": data["master"]["id"], "nama_mk": "Test", "sks": 3, "semester": 2},
            ).status_code
            == 409
        )
        assert (
            client.patch(base + "/mata-kuliah/" + data["paket"]["id"], json={"sks": 4}).status_code
            == 409
        )
        assert client.delete(base + "/mata-kuliah/" + data["paket"]["id"]).status_code == 409
        assert client.put(data["matrix"], json={"items": []}).status_code == 409
        assert client.post(base + "/aktifkan").status_code == 409
        if status == "Aktif":
            assert client.post(base + "/arsipkan").json()["status"] == "Arsip"
    assert client.post(base + "/arsipkan").status_code == 409
    empty = post(client, "/kurikulum", {"kode_kurikulum": "EMPTY", "nama": "Empty"})
    assert client.post("/api/v1/kurikulum/" + empty["id"] + "/aktifkan").status_code == 409


def test_copy_new_ids_snapshot_and_no_academic_children(admin_client, dataset, db):
    client = admin_client
    source_id = dataset["angkatan"].kurikulum_id  # has class/rancangan/CPMK/participants
    source = "/api/v1/kurikulum/" + str(source_id)
    assert client.post(source + "/aktifkan").status_code == 200
    cloned = client.post(source + "/salin", json={"kode_kurikulum": "COPY", "nama": "Copy"})
    assert cloned.status_code == 201, cloned.text
    target_id = cloned.json()["id"]
    target = "/api/v1/kurikulum/" + target_id
    assert cloned.json()["status"] == "Draft"
    paket = client.get(target + "/mata-kuliah").json()[0]
    cpl = client.get(target + "/cpl").json()[0]
    assert paket["id"] != str(dataset["kurikulum_mk"].id)
    assert paket["mk_id"] == str(dataset["mk"].id)
    assert cpl["id"] != client.get(source + "/cpl").json()[0]["id"]
    assert (
        client.get(target + "/mata-kuliah/" + paket["id"] + "/cpl").json()[0]["cpl_id"] == cpl["id"]
    )
    assert not service.used_paket(db, UUID(paket["id"]))
    assert (
        client.patch(
            target + "/mata-kuliah/" + paket["id"], json={"nama_mk": "Copy edited"}
        ).status_code
        == 200
    )
    assert (
        client.patch(target + "/cpl/" + cpl["id"], json={"deskripsi": "Copy edited"}).status_code
        == 200
    )
    assert client.get(source + "/mata-kuliah").json()[0]["nama_mk"] == "Basis Data"
    assert client.get(source + "/cpl").json()[0]["deskripsi"] != "Copy edited"
    before = db.scalar(select(func.count()).select_from(AuditLog))
    assert (
        client.post(
            source + "/salin", json={"kode_kurikulum": "COPY", "nama": "Duplicate"}
        ).status_code
        == 409
    )
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditLog)) == before
    assert client.post(source + "/arsipkan").status_code == 200
    assert (
        client.post(
            source + "/salin", json={"kode_kurikulum": "FROM-ARSIP", "nama": "Archive copy"}
        ).status_code
        == 201
    )


def test_payload_validation_and_duplicates(admin_client, db):
    client = admin_client
    data = build(client)
    base = data["base"]
    before = db.scalar(select(func.count()).select_from(AuditLog))
    assert (
        client.post(
            "/api/v1/mata-kuliah", json={"kode_mk": data["master"]["kode_mk"], "nama_mk": "Dup"}
        ).status_code
        == 409
    )
    assert (
        client.post("/api/v1/kurikulum", json={"kode_kurikulum": "K-1", "nama": "Dup"}).status_code
        == 409
    )
    assert (
        client.post(
            base + "/mata-kuliah",
            json={"mk_id": data["master"]["id"], "nama_mk": "Dup", "sks": 3, "semester": 1},
        ).status_code
        == 409
    )
    assert (
        client.post(
            base + "/cpl", json={"kode_cpl": "P-01", "kategori": "P", "deskripsi": "Dup"}
        ).status_code
        == 409
    )
    invalid = [
        ("/api/v1/mata-kuliah", {"kode_mk": "  ", "nama_mk": "Test"}),
        ("/api/v1/mata-kuliah", {"kode_mk": "VALID", "nama_mk": "Test", "prodi_id": str(uuid4())}),
        ("/api/v1/kurikulum", {"kode_kurikulum": "NO", "nama": "Test", "status": "Aktif"}),
        (base + "/cpl", {"kode_cpl": "CPL", "kategori": "INVALID", "deskripsi": "Test"}),
    ]
    for path, body in invalid:
        assert client.post(path, json=body).status_code == 422
    for value in [0, 9, None, 1.5]:
        assert (
            client.patch(
                base + "/mata-kuliah/" + data["paket"]["id"], json={"semester": value}
            ).status_code
            == 422
        )
    for path, body in [
        (base, {}),
        (base, {"nama": None}),
        (base + "/cpl/" + data["cpl"]["id"], {"deskripsi": None}),
    ]:
        assert client.patch(path, json=body).status_code == 422
    assert (
        client.put(data["matrix"], json={"items": [{"cpl_id": data["cpl"]["id"]}] * 2}).status_code
        == 422
    )
    assert (
        client.put(
            data["matrix"], json={"items": [{"cpl_id": data["cpl"]["id"], "urutan_rps": 0}]}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/mata-kuliah?limit=101").status_code == 422
    assert client.get("/api/v1/kurikulum?offset=-1").status_code == 422
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditLog)) == before
    assert client.get(base + "/mata-kuliah").json()[0]["semester"] == 1


def test_national_cpl_merged_patch_rules(admin_client):
    client = admin_client
    data = build(client)
    base = data["base"]
    payload = {"kode_cpl": "S-01", "kategori": "S", "deskripsi": "Sikap", "nasional": True}
    row = post(client, base.removeprefix("/api/v1") + "/cpl", payload)
    path = base + "/cpl/" + row["id"]
    assert row["prodi_id"] is None
    assert client.patch(path, json={"kategori": "P"}).status_code == 409
    response = client.patch(path, json={"kategori": "P", "nasional": False})
    assert response.status_code == 200 and response.json()["prodi_id"] is not None
    assert client.patch(path, json={"nasional": True}).status_code == 409
    assert (
        client.post(
            base + "/cpl", json={**payload, "kode_cpl": "BAD", "kategori": "KK"}
        ).status_code
        == 409
    )


def test_mapping_version_parent_mismatch_and_atomicity(admin_client, db):
    client = admin_client
    a, b = build(client, "A"), build(client, "B")
    original = client.get(a["matrix"]).json()
    before = db.scalar(select(func.count()).select_from(AuditLog))
    assert (
        client.put(
            a["matrix"],
            json={
                "items": [{"cpl_id": a["cpl"]["id"], "urutan_rps": 2}, {"cpl_id": b["cpl"]["id"]}]
            },
        ).status_code
        == 404
    )
    assert client.get(a["matrix"]).json() == original
    assert (
        client.patch(
            a["base"] + "/cpl/" + b["cpl"]["id"], json={"deskripsi": "Wrong parent"}
        ).status_code
        == 404
    )
    assert client.get(a["base"] + "/mata-kuliah/" + b["paket"]["id"]).status_code == 404
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditLog)) == before
    assert (
        client.put(
            a["matrix"], json={"items": [{"cpl_id": a["cpl"]["id"], "urutan_rps": 3}]}
        ).json()[0]["urutan_rps"]
        == 3
    )


def test_used_context_and_cpmk_link_protected(admin_client, dataset):
    client = admin_client
    base = "/api/v1/kurikulum/" + str(dataset["angkatan"].kurikulum_id)
    path = base + "/mata-kuliah/" + str(dataset["kurikulum_mk"].id)
    assert client.delete(base).status_code == 409
    assert client.delete(path).status_code == 409
    assert client.patch(path, json={"semester": 3}).status_code == 409
    assert client.put(path + "/cpl", json={"items": []}).status_code == 409
    assert len(client.get(path + "/cpl").json()) == 1


def test_role_scope_and_prodi_national_isolation(client, dataset, settings, db):
    admin = dataset["admin"]
    other = Prodi(kode_prodi="OTHER", nama_prodi="Other", jenjang="D4")
    db.add(other)
    db.flush()
    kur = Kurikulum(prodi_id=other.id, kode_kurikulum="OTHER", nama="Other")
    mk = MataKuliah(prodi_id=other.id, kode_mk="OTHER", nama_mk="Other")
    db.add_all([kur, mk])
    db.flush()
    national = MasterCPL(
        kurikulum_id=kur.id, prodi_id=None, kode_cpl="S-01", kategori="S", deskripsi="National"
    )
    db.add(national)
    db.commit()
    assert client.get("/api/v1/mata-kuliah").status_code == 401
    for role in ["dosen", "mahasiswa"]:
        client.headers["Authorization"] = "Bearer " + create_access_token(dataset[role], settings)
        assert client.get("/api/v1/mata-kuliah").status_code == 403
        assert (
            client.post(
                "/api/v1/kurikulum", json={"kode_kurikulum": "FORBIDDEN", "nama": "Forbidden"}
            ).status_code
            == 403
        )
        assert client.get("/api/v1/kurikulum/" + str(kur.id) + "/cpl").status_code == 403
    client.headers["Authorization"] = "Bearer " + create_access_token(admin, settings)
    own = build(client)
    for path in [
        "/api/v1/kurikulum/" + str(kur.id),
        "/api/v1/mata-kuliah/" + str(mk.id),
        "/api/v1/kurikulum/" + str(kur.id) + "/cpl/" + str(national.id),
    ]:
        assert client.get(path).status_code == 404
        assert client.delete(path).status_code == 404
    assert (
        client.post(
            own["base"] + "/mata-kuliah",
            json={"mk_id": str(mk.id), "nama_mk": "Wrong", "sks": 3, "semester": 1},
        ).status_code
        == 404
    )
    assert (
        client.put(own["matrix"], json={"items": [{"cpl_id": str(national.id)}]}).status_code == 404
    )
    assert str(kur.id) not in str(client.get("/api/v1/kurikulum").json())


def test_audit_failure_rolls_back_mutation(admin_client, db, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    data = build(admin_client)
    counts = {
        model: db.scalar(select(func.count()).select_from(model))
        for model in [Kurikulum, KurikulumMK, MasterCPL, AuditLog]
    }

    def fail(*args, **kwargs):
        raise IntegrityError("audit failed", None, Exception())

    monkeypatch.setattr(service, "audit", fail)
    response = admin_client.post(
        "/api/v1/mata-kuliah", json={"kode_mk": "ROLLBACK", "nama_mk": "Rollback"}
    )
    assert response.status_code == 409
    assert db.scalar(select(MataKuliah.id).where(MataKuliah.kode_mk == "ROLLBACK")) is None
    assert (
        admin_client.post(
            data["base"] + "/salin", json={"kode_kurikulum": "ROLLBACK-COPY", "nama": "Rollback"}
        ).status_code
        == 409
    )
    for model, count in counts.items():
        assert db.scalar(select(func.count()).select_from(model)) == count


@pytest.mark.parametrize("activate_first", [True, False])
def test_activation_and_edit_are_serialized(admin_client, dataset, engine, activate_first):
    data = build(admin_client)
    locked = Event()
    finished = Event()
    user_id = dataset["admin"].id
    curriculum_id = UUID(data["kur"]["id"])

    def edit():
        with Session(engine, expire_on_commit=False) as session:
            session.execute(text("SET lock_timeout = '5s'"))
            locked.set()
            try:
                if activate_first:
                    service.update_curriculum(
                        session,
                        session.get(User, user_id),
                        curriculum_id,
                        KurikulumPatch(nama="Race edit"),
                    )
                else:
                    service.transition(session, session.get(User, user_id), curriculum_id, "Aktif")
            except HTTPException as exc:
                return exc.status_code
            finally:
                finished.set()
            return 200

    with Session(engine, expire_on_commit=False) as session:
        user = session.get(User, user_id)
        service.curriculum(session, user, curriculum_id, lock=True)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(edit)
            assert locked.wait(timeout=5)
            # Confirm PostgreSQL has a waiting FOR UPDATE, rather than relying on a sleep.
            import time

            deadline = time.monotonic() + 4
            blocked = False
            with engine.connect() as observer:
                while time.monotonic() < deadline:
                    observer.commit()
                    blocked = observer.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE wait_event_type = 'Lock' AND query LIKE '%kurikulum%FOR UPDATE%')"
                        )
                    )
                    if blocked:
                        break
                    time.sleep(0.02)
            try:
                assert blocked and not finished.is_set()
            finally:
                if activate_first:
                    service.transition(session, user, curriculum_id, "Aktif")
                else:
                    service.replace_matrix(
                        session,
                        user,
                        curriculum_id,
                        UUID(data["paket"]["id"]),
                        MatriksReplace(items=[]),
                    )
            assert future.result(timeout=6) == 409
    result = admin_client.get(data["base"]).json()
    assert result["nama"] == "Kurikulum Baru"
    assert result["status"] == ("Aktif" if activate_first else "Draft")
