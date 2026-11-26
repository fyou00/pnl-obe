from uuid import UUID

from sqlalchemy import select

from app.core.security import create_access_token
from app.models import Angkatan, AuditLog, Kurikulum, Prodi
from app.services.seed import ensure_user


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_self_service_change_password_all_roles_and_session_revocation(
    client, db, dataset, seed_config, settings
):
    for role_key in ("admin", "dosen", "mahasiswa"):
        user = dataset[role_key]
        old_password = getattr(seed_config, f"seed_{role_key}_password").get_secret_value()
        new_password = f"SandiBaru_{role_key}_2026!"

        old_token_a = create_access_token(user, settings)
        old_token_b = create_access_token(user, settings)

        # Wrong current password returns 400 (not 401 so UI does not log out session)
        wrong = client.post(
            "/api/v1/auth/ganti-password",
            headers=_bearer(old_token_a),
            json={"password_lama": "SalahSandi12345", "password_baru": new_password},
        )
        assert wrong.status_code == 400

        # Invalid payloads -> 422
        assert (
            client.post(
                "/api/v1/auth/ganti-password",
                headers=_bearer(old_token_a),
                json={"password_lama": old_password, "password_baru": "pendek"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/auth/ganti-password",
                headers=_bearer(old_token_a),
                json={"password_lama": old_password, "password_baru": old_password},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/auth/ganti-password",
                headers=_bearer(old_token_a),
                json={"password_lama": old_password, "password_baru": "é" * 37},
            ).status_code
            == 422
        )

        changed = client.post(
            "/api/v1/auth/ganti-password",
            headers=_bearer(old_token_a),
            json={"password_lama": old_password, "password_baru": new_password},
        )
        assert changed.status_code == 200, changed.text
        fresh_token = changed.json()["access_token"]
        assert changed.headers["cache-control"] == "no-store"

        # Old tokens are revoked; returned token remains active
        assert client.get("/api/v1/auth/me", headers=_bearer(old_token_a)).status_code == 401
        assert client.get("/api/v1/auth/me", headers=_bearer(old_token_b)).status_code == 401
        assert client.get("/api/v1/auth/me", headers=_bearer(fresh_token)).status_code == 200

        # Old password rejected, new password accepted
        assert (
            client.post(
                "/api/v1/auth/token", data={"username": user.email, "password": old_password}
            ).status_code
            == 401
        )
        relogin = client.post(
            "/api/v1/auth/token", data={"username": user.email, "password": new_password}
        )
        assert relogin.status_code == 200

    audit_rows = list(db.scalars(select(AuditLog).where(AuditLog.aksi == "change_password")))
    assert len(audit_rows) == 3
    for row in audit_rows:
        payload_text = str(row.sesudah)
        assert "password_hash" not in payload_text
        assert "token_version" not in payload_text
        assert "SandiBaru" not in payload_text


def test_admin_user_crud_filters_linking_activation_and_reset_password(
    client, db, dataset, settings
):
    admin_headers = _bearer(create_access_token(dataset["admin"], settings))
    angkatan = dataset["angkatan"]

    # Create Dosen and Mahasiswa (unlinked + linked)
    dosen_resp = client.post(
        "/api/v1/pengguna",
        headers=admin_headers,
        json={
            "nim_nidn": "NIDN-100PCT",
            "nama": "100% Dosen Uji",
            "email": "Dosen.Baru@PNL.AC.ID",
            "role": "Dosen",
            "password": "PasswordDosen123!",
        },
    )
    assert dosen_resp.status_code == 201, dosen_resp.text
    dosen_data = dosen_resp.json()
    assert dosen_data["email"] == "dosen.baru@pnl.ac.id"
    assert dosen_data["angkatan_id"] is None
    assert "password_hash" not in dosen_resp.text
    assert "token_version" not in dosen_resp.text

    mhs_unlinked_resp = client.post(
        "/api/v1/pengguna",
        headers=admin_headers,
        json={
            "nim_nidn": "NIM-UNLINKED-01",
            "nama": "Mahasiswa Belum Angkatan",
            "email": "mhs.unlinked@pnl.ac.id",
            "role": "Mahasiswa",
            "password": "PasswordMhs123!",
        },
    )
    assert mhs_unlinked_resp.status_code == 201, mhs_unlinked_resp.text
    assert mhs_unlinked_resp.json()["angkatan_id"] is None

    mhs_linked_resp = client.post(
        "/api/v1/pengguna",
        headers=admin_headers,
        json={
            "nim_nidn": "NIM-LINKED-01",
            "nama": "Mahasiswa Angkatan",
            "email": "mhs.linked@pnl.ac.id",
            "role": "Mahasiswa",
            "password": "PasswordMhs123!",
            "angkatan_id": str(angkatan.id),
        },
    )
    assert mhs_linked_resp.status_code == 201, mhs_linked_resp.text
    assert mhs_linked_resp.json()["angkatan_id"] == str(angkatan.id)
    assert mhs_linked_resp.json()["tahun_masuk"] == angkatan.tahun_masuk

    # Validation & duplicates
    assert (
        client.post(
            "/api/v1/pengguna",
            headers=admin_headers,
            json={
                "nim_nidn": "NIM-DUP-E",
                "nama": "Dup",
                "email": "DOSEN.BARU@pnl.ac.id",
                "role": "Dosen",
                "password": "PasswordValid123!",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/pengguna",
            headers=admin_headers,
            json={
                "nim_nidn": "NIDN-100PCT",
                "nama": "Dup",
                "email": "unique@pnl.ac.id",
                "role": "Dosen",
                "password": "PasswordValid123!",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/pengguna",
            headers=admin_headers,
            json={
                "nim_nidn": "ADM-NEW",
                "nama": "New Admin",
                "email": "adm.new@pnl.ac.id",
                "role": "Admin",
                "password": "PasswordValid123!",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/pengguna",
            headers=admin_headers,
            json={
                "nim_nidn": "DOS-ANG",
                "nama": "Dosen Angkatan",
                "email": "dos.ang@pnl.ac.id",
                "role": "Dosen",
                "password": "PasswordValid123!",
                "angkatan_id": str(angkatan.id),
            },
        ).status_code
        == 422
    )

    # Literal '%' search, role/aktif/angkatan filters, pagination
    pct_search = client.get("/api/v1/pengguna?q=%25", headers=admin_headers)
    assert pct_search.status_code == 200
    assert [u["id"] for u in pct_search.json()] == [dosen_data["id"]]
    assert (
        len(client.get(f"/api/v1/pengguna?angkatan_id={angkatan.id}", headers=admin_headers).json())
        >= 3
    )
    assert len(client.get("/api/v1/pengguna?limit=2&offset=1", headers=admin_headers).json()) == 2
    assert len(client.get("/api/v1/pengguna?role=Admin", headers=admin_headers).json()) == 1

    # Patch validation, angkatan linking, and rejection on reassigning existing angkatan
    assert (
        client.patch(
            f"/api/v1/pengguna/{mhs_unlinked_resp.json()['id']}", headers=admin_headers, json={}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/pengguna/{mhs_unlinked_resp.json()['id']}",
            headers=admin_headers,
            json={"nama": None},
        ).status_code
        == 422
    )
    linked_after = client.patch(
        f"/api/v1/pengguna/{mhs_unlinked_resp.json()['id']}",
        headers=admin_headers,
        json={"nama": "Mahasiswa Terkait", "angkatan_id": str(angkatan.id)},
    )
    assert linked_after.status_code == 200
    assert linked_after.json()["tahun_masuk"] == angkatan.tahun_masuk

    # Second angkatan -> reject moving already-linked Mahasiswa
    other_angkatan = Angkatan(
        prodi_id=dataset["prodi"].id, tahun_masuk=2027, kurikulum_id=angkatan.kurikulum_id
    )
    db.add(other_angkatan)
    db.commit()
    assert (
        client.patch(
            f"/api/v1/pengguna/{mhs_linked_resp.json()['id']}",
            headers=admin_headers,
            json={"angkatan_id": str(other_angkatan.id)},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/pengguna/{dosen_data['id']}",
            headers=admin_headers,
            json={"angkatan_id": str(angkatan.id)},
        ).status_code
        == 409
    )

    # Deactivate revokes JWT + blocks login; reactivate restores login
    dosen_login = client.post(
        "/api/v1/auth/token",
        data={"username": "dosen.baru@pnl.ac.id", "password": "PasswordDosen123!"},
    )
    assert dosen_login.status_code == 200
    dosen_token = dosen_login.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=_bearer(dosen_token)).status_code == 200

    deact = client.patch(
        f"/api/v1/pengguna/{dosen_data['id']}",
        headers=admin_headers,
        json={"aktif": False},
    )
    assert deact.status_code == 200
    assert deact.json()["aktif"] is False
    assert client.get("/api/v1/auth/me", headers=_bearer(dosen_token)).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/token",
            data={"username": "dosen.baru@pnl.ac.id", "password": "PasswordDosen123!"},
        ).status_code
        == 401
    )

    react = client.patch(
        f"/api/v1/pengguna/{dosen_data['id']}",
        headers=admin_headers,
        json={"aktif": True},
    )
    assert react.status_code == 200
    fresh_login = client.post(
        "/api/v1/auth/token",
        data={"username": "dosen.baru@pnl.ac.id", "password": "PasswordDosen123!"},
    )
    assert fresh_login.status_code == 200
    fresh_dosen_token = fresh_login.json()["access_token"]

    # Admin reset password revokes target session + sets audit reason
    reset_resp = client.post(
        f"/api/v1/pengguna/{dosen_data['id']}/reset-password",
        headers=admin_headers,
        json={"password_baru": "ResetDosen2026!!", "alasan": "Lupa kata sandi"},
    )
    assert reset_resp.status_code == 200
    assert "password_hash" not in reset_resp.text
    assert client.get("/api/v1/auth/me", headers=_bearer(fresh_dosen_token)).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/token",
            data={"username": "dosen.baru@pnl.ac.id", "password": "PasswordDosen123!"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/token",
            data={"username": "dosen.baru@pnl.ac.id", "password": "ResetDosen2026!!"},
        ).status_code
        == 200
    )

    reset_audit = db.scalar(
        select(AuditLog).where(
            AuditLog.entitas == "users",
            AuditLog.entitas_id == UUID(dosen_data["id"]),
            AuditLog.aksi == "reset_password",
        )
    )
    assert reset_audit is not None
    assert reset_audit.alasan == "Lupa kata sandi"
    assert "ResetDosen2026!!" not in str(reset_audit.sesudah)
    assert "password_hash" not in str(reset_audit.sesudah)
    assert "token_version" not in str(reset_audit.sesudah)


def test_admin_protections_rbac_and_prodi_isolation_and_no_secret_leak(
    client, db, dataset, seed_config, settings
):
    admin = dataset["admin"]
    second_admin = ensure_user(
        db,
        dataset["prodi"],
        nama="Admin Kedua",
        nim_nidn="ADM-2",
        email="admin2@example.com",
        password=seed_config.seed_admin_password,
        role="Admin",
    )
    other_prodi = Prodi(kode_prodi="TM", nama_prodi="Teknik Mesin", jenjang="D4")
    db.add(other_prodi)
    db.flush()
    other_kur = Kurikulum(prodi_id=other_prodi.id, kode_kurikulum="TM-2024", nama="TM")
    db.add(other_kur)
    db.flush()
    other_angkatan = Angkatan(prodi_id=other_prodi.id, tahun_masuk=2025, kurikulum_id=other_kur.id)
    db.add(other_angkatan)
    other_user = ensure_user(
        db,
        other_prodi,
        nama="Dosen Prodi Lain",
        nim_nidn="DOS-TM-1",
        email="dos.tm@example.com",
        password=seed_config.seed_dosen_password,
        role="Dosen",
    )
    db.commit()

    admin_headers = _bearer(create_access_token(admin, settings))

    # Self-lockout & other-admin protection
    assert (
        client.patch(
            f"/api/v1/pengguna/{admin.id}", headers=admin_headers, json={"aktif": False}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/pengguna/{admin.id}/reset-password",
            headers=admin_headers,
            json={"password_baru": "AttemptSelfReset123"},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/pengguna/{second_admin.id}", headers=admin_headers, json={"nama": "Hack"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/pengguna/{second_admin.id}/reset-password",
            headers=admin_headers,
            json={"password_baru": "AttemptOtherAdmin123"},
        ).status_code
        == 409
    )

    # Multi-prodi isolation
    listed_ids = {
        u["id"] for u in client.get("/api/v1/pengguna?limit=100", headers=admin_headers).json()
    }
    assert str(other_user.id) not in listed_ids
    assert client.get(f"/api/v1/pengguna/{other_user.id}", headers=admin_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/pengguna/{other_user.id}", headers=admin_headers, json={"nama": "Nope"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/pengguna/{other_user.id}/reset-password",
            headers=admin_headers,
            json={"password_baru": "CrossProdiReset123"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/pengguna",
            headers=admin_headers,
            json={
                "nim_nidn": "MHS-XPRODI",
                "nama": "Mhs Cross Prodi",
                "email": "mhs.xprodi@example.com",
                "role": "Mahasiswa",
                "password": "PasswordValid123!",
                "angkatan_id": str(other_angkatan.id),
            },
        ).status_code
        == 404
    )

    # RBAC: Dosen and Mahasiswa forbidden (403)
    dosen_id = str(dataset["dosen"].id)
    for actor_key in ("dosen", "mahasiswa"):
        headers = _bearer(create_access_token(dataset[actor_key], settings))
        assert client.get("/api/v1/pengguna", headers=headers).status_code == 403
        assert (
            client.post(
                "/api/v1/pengguna",
                headers=headers,
                json={
                    "nim_nidn": "UNAUTH-1",
                    "nama": "Unauth",
                    "email": "unauth@example.com",
                    "role": "Dosen",
                    "password": "PasswordValid123!",
                },
            ).status_code
            == 403
        )
        assert client.get(f"/api/v1/pengguna/{dosen_id}", headers=headers).status_code == 403
        assert (
            client.patch(
                f"/api/v1/pengguna/{dosen_id}", headers=headers, json={"nama": "X"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/pengguna/{dosen_id}/reset-password",
                headers=headers,
                json={"password_baru": "UnauthorizedReset123"},
            ).status_code
            == 403
        )

    # Secret fields never appear in OpenAPI schema
    openapi_text = client.get("/openapi.json").text
    assert "password_hash" not in openapi_text
    assert "token_version" not in openapi_text
