"""All integration tests use real PostgreSQL and disposable databases, never SQLite."""

import os
import secrets
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.main import create_app
from app.models import (
    CPMK,
    CPMKCPL,
    MKCPL,
    Angkatan,
    InstrumenPenilaian,
    KelasMK,
    KelasPeriode,
    KurikulumMK,
    Mahasiswa,
    MahasiswaPeriode,
    MasterCPL,
    MataKuliah,
    PeriodeAkademik,
    PesertaKelasMK,
    Prodi,
    RancanganPenilaian,
    SubCPMK,
    User,
)
from app.services.seed import SeedSettings, ensure_user, seed

BACKEND = Path(__file__).resolve().parents[1]


def alembic_config(connection) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


@pytest.fixture(scope="session")
def postgres_url(tmp_path_factory):
    configured = os.environ.get("TEST_DATABASE_URL")
    if configured:
        yield make_url(configured)
        return
    import pgserver

    server = pgserver.get_server(tmp_path_factory.mktemp("postgres") / "data", cleanup_mode="stop")
    try:
        yield make_url(server.get_uri()).set(drivername="postgresql+psycopg")
    finally:
        server.cleanup()


@pytest.fixture
def db_url(postgres_url):
    name = "obe_test_" + uuid4().hex
    admin_engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = postgres_url.set(database=name)
    try:
        yield url
    finally:
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin_engine.dispose()


@pytest.fixture
def engine(db_url):
    engine = create_engine(db_url)
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def seed_config(db_url):
    return SeedSettings(
        _env_file=None,
        database_url=db_url.render_as_string(hide_password=False),
        seed_admin_nama="Test Admin",
        seed_admin_nim_nidn="ADMIN-TEST",
        seed_admin_email="admin@example.com",
        seed_admin_password=secrets.token_urlsafe(18),
        seed_dosen_nama="Test Dosen",
        seed_dosen_nim_nidn="DOSEN-TEST",
        seed_dosen_email="dosen@example.com",
        seed_dosen_password=secrets.token_urlsafe(18),
        seed_mahasiswa_nama="Test Mahasiswa",
        seed_mahasiswa_nim_nidn="MHS-TEST",
        seed_mahasiswa_email="mahasiswa@example.com",
        seed_mahasiswa_password=secrets.token_urlsafe(18),
    )


@pytest.fixture
def dataset(db, seed_config):
    """Direct fixture writes create context; academic write services are a later phase."""
    seed(db, seed_config, demo=True)
    db.commit()
    admin = db.scalar(select(User).where(User.role == "Admin"))
    dosen = db.scalar(select(User).where(User.role == "Dosen"))
    mahasiswa = db.scalar(select(User).where(User.role == "Mahasiswa"))
    prodi = db.get(Prodi, admin.prodi_id)
    angkatan = db.scalar(select(Angkatan))
    period = PeriodeAkademik(prodi_id=prodi.id, tahun_mulai=2026, semester="Ganjil")
    mk = MataKuliah(prodi_id=prodi.id, kode_mk="TI001", nama_mk="Basis Data")
    db.add_all([period, mk])
    db.flush()
    kurikulum_mk = KurikulumMK(
        kurikulum_id=angkatan.kurikulum_id, mk_id=mk.id, nama_mk=mk.nama_mk, sks=3, semester=1
    )
    cpl = MasterCPL(
        kurikulum_id=angkatan.kurikulum_id,
        prodi_id=prodi.id,
        kode_cpl="CPL-01",
        kategori="P",
        deskripsi="Menguasai basis data",
    )
    db.add_all([kurikulum_mk, cpl])
    db.flush()
    db.add(MKCPL(kurikulum_mk_id=kurikulum_mk.id, cpl_id=cpl.id))
    design = RancanganPenilaian(
        periode_id=period.id, kurikulum_mk_id=kurikulum_mk.id, dosen_id=dosen.id
    )
    class_a = KelasPeriode(
        periode_id=period.id, angkatan_id=angkatan.id, kode_kelas="A", semester_studi=1
    )
    class_b = KelasPeriode(
        periode_id=period.id, angkatan_id=angkatan.id, kode_kelas="B", semester_studi=1
    )
    db.add_all([design, class_a, class_b])
    db.flush()
    course_a = KelasMK(
        kelas_periode_id=class_a.id, kurikulum_mk_id=kurikulum_mk.id, rancangan_id=design.id
    )
    course_b = KelasMK(
        kelas_periode_id=class_b.id, kurikulum_mk_id=kurikulum_mk.id, rancangan_id=design.id
    )
    cpmk = CPMK(rancangan_id=design.id, kode_cpmk="CPMK-1", deskripsi="Merancang basis data")
    db.add_all([course_a, course_b, cpmk])
    db.flush()
    db.add(CPMKCPL(cpmk_id=cpmk.id, cpl_id=cpl.id))
    sub = SubCPMK(cpmk_id=cpmk.id, kode_sub="SUB-1", deskripsi="Merancang tabel")
    db.add(sub)
    db.flush()
    instrument = InstrumenPenilaian(
        sub_cpmk_id=sub.id, nama_instrumen="Tugas 1", jenis_instrumen="Tugas", bobot_persentase=100
    )
    db.add(instrument)
    db.add(
        MahasiswaPeriode(
            mahasiswa_id=mahasiswa.id,
            periode_id=period.id,
            kelas_periode_id=class_a.id,
            status="Aktif",
        )
    )
    db.add(PesertaKelasMK(kelas_mk_id=course_a.id, mahasiswa_id=mahasiswa.id, mk_id=mk.id))
    outsider = ensure_user(
        db,
        prodi,
        nama="Other lecturer",
        nim_nidn="OTHER-DOSEN",
        email="other@example.com",
        password=seed_config.seed_dosen_password,
        role="Dosen",
    )
    other_student = ensure_user(
        db,
        prodi,
        nama="Other student",
        nim_nidn="OTHER-MHS",
        email="other-mhs@example.com",
        password=seed_config.seed_mahasiswa_password,
        role="Mahasiswa",
    )
    db.add(Mahasiswa(id=other_student.id, angkatan_id=angkatan.id))
    db.commit()
    return dict(
        admin=admin,
        dosen=dosen,
        mahasiswa=mahasiswa,
        outsider=outsider,
        other_student=other_student,
        prodi=prodi,
        angkatan=angkatan,
        period=period,
        mk=mk,
        kurikulum_mk=kurikulum_mk,
        design=design,
        course_a=course_a,
        course_b=course_b,
        instrument=instrument,
    )


@pytest.fixture
def settings(db_url):
    return Settings(
        _env_file=None,
        database_url=db_url.render_as_string(hide_password=False),
        jwt_secret_key=secrets.token_urlsafe(48),
    )


@pytest.fixture
def client(settings, engine):
    app = create_app(settings)
    with TestClient(app) as client:
        yield client
