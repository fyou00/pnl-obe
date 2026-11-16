"""Idempotent bootstrap. Credentials come only from environment/.env."""

import argparse

from pydantic import EmailStr, Field, SecretStr, TypeAdapter
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import ENV_FILE, DatabaseSettings
from app.core.database import Database
from app.core.security import hash_password
from app.models import Angkatan, Kurikulum, Mahasiswa, Prodi, User


class SeedSettings(DatabaseSettings):
    seed_prodi_kode: str = Field(default="TI", min_length=1, max_length=20)
    seed_prodi_nama: str = Field(default="Teknik Informatika", min_length=1, max_length=100)
    seed_prodi_jenjang: str = Field(default="D4", min_length=1, max_length=10)
    seed_admin_nama: str = Field(min_length=1, max_length=100)
    seed_admin_nim_nidn: str = Field(min_length=1, max_length=20)
    seed_admin_email: EmailStr
    seed_admin_password: SecretStr
    seed_dosen_nama: str = "Contoh Dosen"
    seed_dosen_nim_nidn: str | None = None
    seed_dosen_email: str | None = None
    seed_dosen_password: SecretStr | None = None
    seed_mahasiswa_nama: str = "Contoh Mahasiswa"
    seed_mahasiswa_nim_nidn: str | None = None
    seed_mahasiswa_email: str | None = None
    seed_mahasiswa_password: SecretStr | None = None
    seed_angkatan: int = Field(default=2026, ge=2000, le=2100)


def ensure_user(
    db: Session,
    prodi: Prodi,
    *,
    nama: str,
    nim_nidn: str,
    email: str,
    password: SecretStr,
    role: str,
) -> User:
    email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    if not nama or len(nama) > 100 or not nim_nidn or len(nim_nidn) > 20:
        raise ValueError("Identitas akun seed tidak valid")
    raw_password = password.get_secret_value()
    if not 12 <= len(raw_password.encode()) <= 72:
        raise ValueError("Password seed harus 12–72 byte UTF-8")
    users = list(
        db.scalars(select(User).where(or_(User.email == email, User.nim_nidn == nim_nidn)))
    )
    if users:
        if len(users) != 1:
            raise ValueError("Email dan NIM/NIDN seed bertabrakan dengan akun berbeda")
        user = users[0]
        if (
            user.email != email
            or user.nim_nidn != nim_nidn
            or user.prodi_id != prodi.id
            or user.role != role
        ):
            raise ValueError("Identitas seed bertabrakan dengan akun yang sudah ada")
        return user  # Do not silently reset passwords or user attributes on reruns.
    user = User(
        prodi_id=prodi.id,
        nama=nama,
        nim_nidn=nim_nidn,
        email=email,
        password_hash=hash_password(raw_password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def seed(db: Session, config: SeedSettings, *, demo: bool = False) -> dict[str, str]:
    """Caller owns one transaction; failure must roll back the entire seed."""
    prodi = db.scalar(select(Prodi).where(Prodi.kode_prodi == config.seed_prodi_kode))
    if prodi is None:
        prodi = Prodi(
            kode_prodi=config.seed_prodi_kode,
            nama_prodi=config.seed_prodi_nama,
            jenjang=config.seed_prodi_jenjang,
        )
        db.add(prodi)
        db.flush()
    elif prodi.nama_prodi != config.seed_prodi_nama or prodi.jenjang != config.seed_prodi_jenjang:
        raise ValueError("Kode prodi seed sudah dipakai dengan identitas berbeda")
    admin = ensure_user(
        db,
        prodi,
        nama=config.seed_admin_nama,
        nim_nidn=config.seed_admin_nim_nidn,
        email=str(config.seed_admin_email),
        password=config.seed_admin_password,
        role="Admin",
    )
    result = {"prodi_id": str(prodi.id), "admin_id": str(admin.id)}
    if not demo:
        return result
    for prefix, role in [("dosen", "Dosen"), ("mahasiswa", "Mahasiswa")]:
        nim = getattr(config, f"seed_{prefix}_nim_nidn")
        email = getattr(config, f"seed_{prefix}_email")
        password = getattr(config, f"seed_{prefix}_password")
        if not nim or not email or not password:
            raise ValueError(f"Lengkapi kredensial SEED_{prefix.upper()} di .env untuk --demo")
        user = ensure_user(
            db,
            prodi,
            nama=getattr(config, f"seed_{prefix}_nama"),
            nim_nidn=nim,
            email=email,
            password=password,
            role=role,
        )
        result[f"{prefix}_id"] = str(user.id)
        if role == "Mahasiswa":
            angkatan = db.scalar(
                select(Angkatan).where(
                    Angkatan.prodi_id == prodi.id, Angkatan.tahun_masuk == config.seed_angkatan
                )
            )
            if angkatan is None:
                code = f"DEMO-{config.seed_angkatan}"
                kurikulum = db.scalar(
                    select(Kurikulum).where(
                        Kurikulum.prodi_id == prodi.id, Kurikulum.kode_kurikulum == code
                    )
                )
                if kurikulum is None:
                    kurikulum = Kurikulum(
                        prodi_id=prodi.id, kode_kurikulum=code, nama="Kurikulum contoh (draft)"
                    )
                    db.add(kurikulum)
                    db.flush()
                angkatan = Angkatan(
                    prodi_id=prodi.id, tahun_masuk=config.seed_angkatan, kurikulum_id=kurikulum.id
                )
                db.add(angkatan)
                db.flush()
            mahasiswa = db.get(Mahasiswa, user.id)
            if mahasiswa is None:
                db.add(Mahasiswa(id=user.id, angkatan_id=angkatan.id))
            elif mahasiswa.angkatan_id != angkatan.id:
                raise ValueError("Mahasiswa seed sudah terdaftar pada angkatan berbeda")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed awal PNL OBE, kredensial dari backend/.env")
    parser.add_argument(
        "--demo", action="store_true", help="Tambahkan akun contoh Dosen/Mahasiswa dan angkatan"
    )
    args = parser.parse_args()
    config = SeedSettings(_env_file=ENV_FILE)
    database = Database(config)
    try:
        with database.session_factory.begin() as db:
            seed(db, config, demo=args.demo)
        print("Seed berhasil; akun yang sudah ada tidak diubah. Kredensial tidak ditampilkan.")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
