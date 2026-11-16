"""Check the running localhost API without printing credentials or access tokens."""

import httpx

from app.services.seed import SeedSettings


def main():
    config = SeedSettings()
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=10) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").json() == {"status": "ready"}
        for role in ["Admin", "Dosen", "Mahasiswa"]:
            prefix = role.lower()
            password = getattr(config, f"seed_{prefix}_password")
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "username": str(getattr(config, f"seed_{prefix}_email")),
                    "password": password.get_secret_value(),
                },
            )
            assert response.status_code == 200
            headers = {"Authorization": "Bearer " + response.json()["access_token"]}
            profile = client.get("/api/v1/auth/me", headers=headers)
            assert profile.status_code == 200 and profile.json()["role"] == role
            assert "password_hash" not in profile.text
            assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
        print("HTTP smoke OK: health, readiness, login/me/logout untuk tiga peran.")


if __name__ == "__main__":
    main()
