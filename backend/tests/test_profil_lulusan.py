from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models import AuditLog, Kurikulum, MasterCPL, Prodi, ProfilLulusan
from app.models.curriculum import PLCPL
from app.services.seed import ensure_user


@pytest.fixture
def admin_client(client, dataset, settings):
    client.headers["Authorization"] = "Bearer " + create_access_token(dataset["admin"], settings)
    return client


def _create_base_draft(client, suffix="PL1"):
    mk = client.post(
        "/api/v1/mata-kuliah", json={"kode_mk": f"MK-{suffix}", "nama_mk": f"MK {suffix}"}
    )
    assert mk.status_code == 201, mk.text
    kur = client.post(
        "/api/v1/kurikulum",
        json={"kode_kurikulum": f"KUR-{suffix}", "nama": f"Kurikulum {suffix}"},
    )
    assert kur.status_code == 201, kur.text
    kur_id = kur.json()["id"]
    paket = client.post(
        f"/api/v1/kurikulum/{kur_id}/mata-kuliah",
        json={"mk_id": mk.json()["id"], "nama_mk": f"MK {suffix}", "sks": 3, "semester": 1},
    )
    assert paket.status_code == 201, paket.text
    cpls = []
    for code, cat in [("CPL-01", "S"), ("CPL-02", "KK"), ("CPL-03", "P")]:
        resp = client.post(
            f"/api/v1/kurikulum/{kur_id}/cpl",
            json={"kode_cpl": code, "kategori": cat, "deskripsi": f"Deskripsi {code}"},
        )
        assert resp.status_code == 201, resp.text
        cpls.append(resp.json())
    mat = client.put(
        f"/api/v1/kurikulum/{kur_id}/mata-kuliah/{paket.json()['id']}/cpl",
        json={"items": [{"cpl_id": cpls[0]["id"], "urutan_rps": 1}]},
    )
    assert mat.status_code == 200, mat.text
    return {"kur": kur.json(), "paket": paket.json(), "cpls": cpls}


def test_profil_lulusan_crud_validation_search_and_audit(admin_client, db):
    client = admin_client
    ctx = _create_base_draft(client, "CRUD")
    base = f"/api/v1/kurikulum/{ctx['kur']['id']}/profil-lulusan"

    r1 = client.post(
        base,
        json={
            "kode_pl": "PL-01",
            "nama_pl": "Rekayasa Aplikasi",
            "bidang_kerja": "  Web Developer, Backend Engineer  ",
            "deskripsi": "Mampu merancang aplikasi.",
        },
    )
    assert r1.status_code == 201, r1.text
    pl1 = r1.json()
    assert pl1["bidang_kerja"] == "Web Developer, Backend Engineer"

    r2 = client.post(
        base,
        json={
            "kode_pl": "PL-02",
            "nama_pl": "100% Data Science",
            "bidang_kerja": "   ",
            "deskripsi": "Mengolah data.",
        },
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["bidang_kerja"] is None

    # Duplicate kode_pl -> 409
    dup = client.post(
        base,
        json={"kode_pl": "PL-01", "nama_pl": "Duplikat", "deskripsi": "Duplikat"},
    )
    assert dup.status_code == 409

    # List, pagination, literal % search
    assert len(client.get(base).json()) == 2
    assert len(client.get(base + "?limit=1&offset=1").json()) == 1
    assert len(client.get(base + "?q=%25").json()) == 1
    assert client.get(base + "?q=%25").json()[0]["kode_pl"] == "PL-02"
    assert client.get(base + "/" + pl1["id"]).json()["nama_pl"] == "Rekayasa Aplikasi"

    # Patch validation
    assert client.patch(base + "/" + pl1["id"], json={}).status_code == 422
    assert client.patch(base + "/" + pl1["id"], json={"deskripsi": None}).status_code == 422
    cleared = client.patch(base + "/" + pl1["id"], json={"bidang_kerja": None})
    assert cleared.status_code == 200
    assert cleared.json()["bidang_kerja"] is None

    updated = client.patch(
        base + "/" + pl1["id"],
        json={"nama_pl": "Application Engineer", "bidang_kerja": "QA Engineer"},
    )
    assert updated.status_code == 200
    assert updated.json()["nama_pl"] == "Application Engineer"
    assert updated.json()["bidang_kerja"] == "QA Engineer"

    assert client.delete(base + "/" + pl1["id"]).status_code == 204
    assert client.get(base + "/" + pl1["id"]).status_code == 404

    logs = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.entitas == "profil_lulusan", AuditLog.entitas_id == UUID(pl1["id"]))
            .order_by(AuditLog.waktu)
        )
    )
    assert [log.aksi for log in logs] == ["create", "update", "update", "delete"]


def test_pl_cpl_matrix_constraints_cascade_and_audit(admin_client, db):
    client = admin_client
    ctx1 = _create_base_draft(client, "M1")
    ctx2 = _create_base_draft(client, "M2")
    kur1_id = ctx1["kur"]["id"]
    base1 = f"/api/v1/kurikulum/{kur1_id}/profil-lulusan"

    pl = client.post(
        base1, json={"kode_pl": "PL-01", "nama_pl": "System Engineer", "deskripsi": "Sistem."}
    ).json()
    matrix_url = f"{base1}/{pl['id']}/cpl"

    # Duplicate cpl_id -> 422
    assert (
        client.put(
            matrix_url, json={"cpl_ids": [ctx1["cpls"][0]["id"], ctx1["cpls"][0]["id"]]}
        ).status_code
        == 422
    )
    # Cross-curriculum cpl_id -> 404
    assert client.put(matrix_url, json={"cpl_ids": [ctx2["cpls"][0]["id"]]}).status_code == 404

    # Replace matrix atomically
    put_resp = client.put(
        matrix_url, json={"cpl_ids": [ctx1["cpls"][2]["id"], ctx1["cpls"][1]["id"]]}
    )
    assert put_resp.status_code == 200
    assert [row["cpl_id"] for row in put_resp.json()] == [
        ctx1["cpls"][1]["id"],
        ctx1["cpls"][2]["id"],
    ]

    # Deleting linked CPL is blocked (RESTRICT -> 409) until unlinked
    cpl2_url = f"/api/v1/kurikulum/{kur1_id}/cpl/{ctx1['cpls'][2]['id']}"
    assert client.delete(cpl2_url).status_code == 409
    assert client.put(matrix_url, json={"cpl_ids": [ctx1["cpls"][1]["id"]]}).status_code == 200
    assert client.delete(cpl2_url).status_code == 204

    # Audit log recorded replace_pl_matrix
    audit_actions = list(
        db.scalars(
            select(AuditLog.aksi)
            .where(AuditLog.entitas == "profil_lulusan", AuditLog.entitas_id == UUID(pl["id"]))
            .order_by(AuditLog.waktu)
        )
    )
    assert "replace_pl_matrix" in audit_actions

    # Deleting PL cascades its pl_cpl rows cleanly while leaving MasterCPL intact
    assert client.delete(f"{base1}/{pl['id']}").status_code == 204
    assert (
        db.scalar(
            select(func.count()).select_from(PLCPL).where(PLCPL.profil_lulusan_id == UUID(pl["id"]))
        )
        == 0
    )
    assert db.get(MasterCPL, UUID(ctx1["cpls"][1]["id"])) is not None


def test_pl_immutability_clone_and_draft_curriculum_delete(admin_client, db):
    client = admin_client
    ctx = _create_base_draft(client, "CLONE")
    kur_id = ctx["kur"]["id"]
    base = f"/api/v1/kurikulum/{kur_id}/profil-lulusan"

    pl = client.post(
        base,
        json={
            "kode_pl": "PL-01",
            "nama_pl": "AI Engineer",
            "bidang_kerja": "ML Engineer",
            "deskripsi": "Membangun sistem cerdas.",
        },
    ).json()
    assert (
        client.put(
            f"{base}/{pl['id']}/cpl", json={"cpl_ids": [ctx["cpls"][0]["id"], ctx["cpls"][1]["id"]]}
        ).status_code
        == 200
    )

    assert client.post(f"/api/v1/kurikulum/{kur_id}/aktifkan").status_code == 200

    for status in ("Aktif", "Arsip"):
        assert client.get(base).status_code == 200
        assert (
            client.post(
                base, json={"kode_pl": "PL-09", "nama_pl": "X", "deskripsi": "X"}
            ).status_code
            == 409
        )
        assert client.patch(f"{base}/{pl['id']}", json={"nama_pl": "Y"}).status_code == 409
        assert client.delete(f"{base}/{pl['id']}").status_code == 409
        assert client.put(f"{base}/{pl['id']}/cpl", json={"cpl_ids": []}).status_code == 409
        if status == "Aktif":
            assert client.post(f"/api/v1/kurikulum/{kur_id}/arsipkan").status_code == 200

    # Clone archived curriculum copies PL + remapped PL-CPL cleanly
    cloned_resp = client.post(
        f"/api/v1/kurikulum/{kur_id}/salin",
        json={"kode_kurikulum": "KUR-CLONE-V2", "nama": "Kurikulum V2"},
    )
    assert cloned_resp.status_code == 201, cloned_resp.text
    cloned_id = cloned_resp.json()["id"]

    cloned_pls = client.get(f"/api/v1/kurikulum/{cloned_id}/profil-lulusan").json()
    assert len(cloned_pls) == 1
    assert cloned_pls[0]["id"] != pl["id"]
    assert cloned_pls[0]["kode_pl"] == "PL-01"
    assert cloned_pls[0]["bidang_kerja"] == "ML Engineer"

    cloned_cpls = client.get(f"/api/v1/kurikulum/{cloned_id}/cpl").json()
    cloned_cpl_ids = {c["id"] for c in cloned_cpls}
    assert cloned_cpl_ids.isdisjoint({c["id"] for c in ctx["cpls"]})

    cloned_links = client.get(
        f"/api/v1/kurikulum/{cloned_id}/profil-lulusan/{cloned_pls[0]['id']}/cpl"
    ).json()
    assert len(cloned_links) == 2
    assert {row["cpl_id"] for row in cloned_links}.issubset(cloned_cpl_ids)

    # Deleting Draft curriculum atomically deletes its PL and PL-CPL rows
    assert client.delete(f"/api/v1/kurikulum/{cloned_id}").status_code == 204
    assert db.get(Kurikulum, UUID(cloned_id)) is None
    assert (
        db.scalar(
            select(func.count())
            .select_from(ProfilLulusan)
            .where(ProfilLulusan.kurikulum_id == UUID(cloned_id))
        )
        == 0
    )


def test_pl_rbac_and_ringkasan_scoping_across_roles_and_prodi(
    client, db, dataset, seed_config, settings
):
    admin = dataset["admin"]
    dosen = dataset["dosen"]
    mahasiswa = dataset["mahasiswa"]

    # Create another prodi with an active curriculum and PL
    other_prodi = Prodi(kode_prodi="SI", nama_prodi="Sistem Informasi", jenjang="D4")
    db.add(other_prodi)
    db.flush()
    other_admin = ensure_user(
        db,
        other_prodi,
        nama="Admin SI",
        nim_nidn="ADM-SI",
        email="admin-si@example.com",
        password=seed_config.seed_admin_password,
        role="Admin",
    )
    other_kur = Kurikulum(prodi_id=other_prodi.id, kode_kurikulum="SI-2024", nama="Kurikulum SI")
    db.add(other_kur)
    db.flush()
    other_cpl = MasterCPL(
        kurikulum_id=other_kur.id,
        prodi_id=other_prodi.id,
        kode_cpl="CPL-SI-1",
        kategori="P",
        deskripsi="SI CPL",
    )
    other_pl = ProfilLulusan(
        kurikulum_id=other_kur.id,
        kode_pl="PL-SI-1",
        nama_pl="IS Analyst",
        deskripsi="SI PL",
    )
    db.add_all([other_cpl, other_pl])
    db.flush()
    db.add(PLCPL(profil_lulusan_id=other_pl.id, cpl_id=other_cpl.id))
    other_kur.status = "Aktif"
    db.commit()

    # Admin creates an Aktif and a Draft curriculum in own prodi (plus student's DEMO-2026 Draft)
    client.headers["Authorization"] = "Bearer " + create_access_token(admin, settings)
    active_ctx = _create_base_draft(client, "ACT")
    active_id = active_ctx["kur"]["id"]
    active_pl = client.post(
        f"/api/v1/kurikulum/{active_id}/profil-lulusan",
        json={"kode_pl": "PL-ACT", "nama_pl": "Active Engineer", "deskripsi": "Aktif."},
    ).json()
    client.put(
        f"/api/v1/kurikulum/{active_id}/profil-lulusan/{active_pl['id']}/cpl",
        json={"cpl_ids": [active_ctx["cpls"][0]["id"]]},
    )
    assert client.post(f"/api/v1/kurikulum/{active_id}/aktifkan").status_code == 200

    draft_ctx = _create_base_draft(client, "DFT")
    draft_id = draft_ctx["kur"]["id"]

    # Seed student's own angkatan curriculum (DEMO-2026) with a PL so student ringkasan is verifiable
    student_kur_id = str(dataset["angkatan"].kurikulum_id)
    student_pl = client.post(
        f"/api/v1/kurikulum/{student_kur_id}/profil-lulusan",
        json={"kode_pl": "PL-MHS", "nama_pl": "Student Track", "deskripsi": "Jalur mhs."},
    ).json()

    # Admin ringkasan checks
    admin_default = client.get("/api/v1/profil-lulusan/ringkasan")
    assert admin_default.status_code == 200
    assert admin_default.json()["kurikulum_id"] == active_id
    assert len(admin_default.json()["profil_lulusan"]) == 1
    assert admin_default.json()["profil_lulusan"][0]["cpl_ids"] == [active_ctx["cpls"][0]["id"]]
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={draft_id}").status_code == 200
    )
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={other_kur.id}").status_code
        == 404
    )

    # Dosen & Mahasiswa forbidden from Admin write endpoints (403)
    for actor in (dosen, mahasiswa):
        client.headers["Authorization"] = "Bearer " + create_access_token(actor, settings)
        assert client.get(f"/api/v1/kurikulum/{active_id}/profil-lulusan").status_code == 403
        assert (
            client.post(
                f"/api/v1/kurikulum/{draft_id}/profil-lulusan",
                json={"kode_pl": "PL-X", "nama_pl": "X", "deskripsi": "X"},
            ).status_code
            == 403
        )
        assert (
            client.put(
                f"/api/v1/kurikulum/{draft_id}/profil-lulusan/{student_pl['id']}/cpl",
                json={"cpl_ids": []},
            ).status_code
            == 403
        )

    # Dosen ringkasan sees Aktif/Arsip in own prodi, blocked from Draft & other prodi
    client.headers["Authorization"] = "Bearer " + create_access_token(dosen, settings)
    dosen_default = client.get("/api/v1/profil-lulusan/ringkasan")
    assert dosen_default.status_code == 200
    assert dosen_default.json()["kurikulum_id"] == active_id
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={draft_id}").status_code == 404
    )
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={other_kur.id}").status_code
        == 404
    )

    # Mahasiswa ringkasan resolves own angkatan curriculum and blocks any other curriculum/prodi
    client.headers["Authorization"] = "Bearer " + create_access_token(mahasiswa, settings)
    mhs_default = client.get("/api/v1/profil-lulusan/ringkasan")
    assert mhs_default.status_code == 200
    assert mhs_default.json()["kurikulum_id"] == student_kur_id
    assert mhs_default.json()["profil_lulusan"][0]["kode_pl"] == "PL-MHS"
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={student_kur_id}").status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={active_id}").status_code == 404
    )
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={other_kur.id}").status_code
        == 404
    )

    # Other admin isolated to other_prodi
    client.headers["Authorization"] = "Bearer " + create_access_token(other_admin, settings)
    other_res = client.get("/api/v1/profil-lulusan/ringkasan")
    assert other_res.status_code == 200
    assert other_res.json()["kurikulum_id"] == str(other_kur.id)
    assert (
        client.get(f"/api/v1/profil-lulusan/ringkasan?kurikulum_id={active_id}").status_code == 404
    )
