from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import update

from app.core.security import create_access_token, hash_password, verify_password
from app.models import Prodi, User


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_each_role_and_public_response(client, dataset, seed_config):
    for role in ["admin", "dosen", "mahasiswa"]:
        email = getattr(seed_config, f"seed_{role}_email")
        password = getattr(seed_config, f"seed_{role}_password").get_secret_value()
        login = client.post(
            "/api/v1/auth/token", data={"username": str(email).upper(), "password": password}
        )
        assert login.status_code == 200
        assert login.headers["cache-control"] == "no-store"
        payload = login.json()
        response = client.get("/api/v1/auth/me", headers=bearer(payload["access_token"]))
        assert response.status_code == 200
        assert response.json()["role"] == dataset[role].role
        assert "password_hash" not in response.text
        assert "token_version" not in response.text
    assert "password_hash" not in client.get("/openapi.json").text


def test_wrong_password_unknown_account_and_inactive(client, db, dataset, seed_config):
    for email in [str(seed_config.seed_admin_email), "unknown@example.com"]:
        response = client.post("/api/v1/auth/token", data={"username": email, "password": "wrong"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    db.execute(update(User).where(User.id == dataset["admin"].id).values(aktif=False))
    db.commit()
    assert (
        client.post(
            "/api/v1/auth/token",
            data={
                "username": str(seed_config.seed_admin_email),
                "password": seed_config.seed_admin_password.get_secret_value(),
            },
        ).status_code
        == 401
    )


def test_token_missing_tampered_expired_and_wrong_audience(client, dataset, settings):
    user = dataset["admin"]
    token = create_access_token(user, settings)
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        audience=settings.jwt_audience,
    )
    expired = jwt.encode(
        {**claims, "exp": datetime.now(UTC) - timedelta(seconds=1)},
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    wrong_audience = jwt.encode(
        {**claims, "aud": "other-app"},
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    assert client.get("/api/v1/auth/me").status_code == 401
    for invalid in ["not-a-jwt", token + "broken", expired, wrong_audience]:
        assert client.get("/api/v1/auth/me", headers=bearer(invalid)).status_code == 401


def test_logout_revokes_all_sessions(client, dataset, settings):
    tokens = [create_access_token(dataset["admin"], settings) for _ in range(2)]
    assert client.post("/api/v1/auth/logout", headers=bearer(tokens[0])).status_code == 204
    for token in tokens:
        assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401


def test_live_role_account_and_prodi_checks(client, db, dataset, settings):
    token = create_access_token(dataset["admin"], settings)
    headers = bearer(token)
    url = f"/api/v1/kelas-mk/{dataset['course_a'].id}/peserta"
    assert client.get(url, headers=headers).status_code == 200
    db.execute(update(User).where(User.id == dataset["admin"].id).values(role="Mahasiswa"))
    db.commit()
    assert client.get(url, headers=headers).status_code == 403
    db.execute(update(Prodi).where(Prodi.id == dataset["prodi"].id).values(aktif=False))
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_class_scope_and_readonly_student(client, db, dataset, settings):
    def headers(role):
        return bearer(create_access_token(dataset[role], settings))

    a, b, period = dataset["course_a"].id, dataset["course_b"].id, dataset["period"].id
    for role, expected in [
        ("admin", {str(a), str(b)}),
        ("dosen", {str(a), str(b)}),
        ("mahasiswa", {str(a)}),
        ("outsider", set()),
        ("other_student", set()),
    ]:
        response = client.get(f"/api/v1/kelas-mk?periode_id={period}", headers=headers(role))
        assert response.status_code == 200
        assert {row["id"] for row in response.json()} == expected
    assert client.get(f"/api/v1/kelas-mk/{b}", headers=headers("mahasiswa")).status_code == 404
    assert client.get(f"/api/v1/kelas-mk/{a}", headers=headers("outsider")).status_code == 404
    assert (
        client.get(f"/api/v1/kelas-mk/{a}/peserta", headers=headers("mahasiswa")).status_code == 403
    )
    assert client.get(f"/api/v1/kelas-mk/{a}/peserta", headers=headers("dosen")).json() == [
        str(dataset["mahasiswa"].id)
    ]
    assert (
        client.post(f"/api/v1/kelas-mk/{a}", headers=headers("mahasiswa"), json={}).status_code
        == 405
    )
    other = Prodi(kode_prodi="OTHER", nama_prodi="Other", jenjang="D4")
    db.add(other)
    db.flush()
    db.execute(update(User).where(User.id == dataset["admin"].id).values(prodi_id=other.id))
    db.commit()
    assert client.get(f"/api/v1/kelas-mk/{a}", headers=headers("admin")).status_code == 404


def test_bcrypt_utf8_limit_and_no_truncation():
    password = "a" * 72
    digest = hash_password(password)
    assert verify_password(password, digest)
    assert not verify_password(password + "b", digest)
    assert not verify_password("wrong", digest)
    with pytest.raises(ValueError):
        hash_password("é" * 37)
