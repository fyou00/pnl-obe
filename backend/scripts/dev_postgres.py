"""Optional local development PostgreSQL for macOS/Linux, not a production server."""

import argparse
import os
import secrets
import time
from pathlib import Path

import pgserver
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--init-env", action="store_true", help="Buat .env lokal baru jika belum ada"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    local = root / ".local"
    local.mkdir(mode=0o700, exist_ok=True)
    server = pgserver.get_server(local / "postgres", cleanup_mode="stop")
    admin_engine = create_engine(
        make_url(server.get_uri()).set(drivername="postgresql+psycopg"),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as connection:
            if not connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = 'pnl_obe_dev'")
            ):
                connection.execute(text("CREATE DATABASE pnl_obe_dev"))
        url = make_url(server.get_uri("pnl_obe_dev")).set(drivername="postgresql+psycopg")
        if args.init_env:
            try:
                descriptor = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                print(
                    ".env sudah ada; tidak ditimpa. Pastikan DATABASE_URL sesuai server lokal ini."
                )
            else:
                with os.fdopen(descriptor, "w") as env:
                    env.write(f"DATABASE_URL={url.render_as_string(hide_password=False)}\n")
                    env.write(f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}\n")
                    env.write('CORS_ORIGINS=["http://localhost:5173"]\n')
                    for role, name, nim in [
                        ("ADMIN", "Administrator TI Lokal", "DEV-ADMIN"),
                        ("DOSEN", "Contoh Dosen", "DEV-DOSEN"),
                        ("MAHASISWA", "Contoh Mahasiswa", "DEV-MHS"),
                    ]:
                        env.write(f"SEED_{role}_NAMA={name}\nSEED_{role}_NIM_NIDN={nim}\n")
                        env.write(f"SEED_{role}_EMAIL={role.lower()}@example.com\n")
                        env.write(f"SEED_{role}_PASSWORD={secrets.token_urlsafe(24)}\n")
                print(
                    ".env lokal dibuat dengan secret/password acak. Kredensial hanya di file tersebut."
                )
        print("PostgreSQL development berjalan lewat Unix socket; Ctrl+C untuk berhenti.")
        print("Terminal lain: alembic upgrade head, lalu python -m app.services.seed --demo.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        admin_engine.dispose()
        server.cleanup()


if __name__ == "__main__":
    main()
